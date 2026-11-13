# app/routers/auth.py
import logging
import time
from datetime import timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.token_claims import claims_match_user, parse_subject, password_fingerprint
from app.core.config import settings
from app.routers.deps import DBDep, get_current_active_user
from app.schemas.user import (
    LogoutRequest,
    Token,
    TokenRefresh,
    UserCreate,
    UserInDB,
)
from app.services.auth_service import AuthService

router = APIRouter()
logger = logging.getLogger(__name__)


AUTH_MODE_HEADER = "x-auth-mode"
COOKIE_PATH = "/api/v1/auth"


def _cookie_mode(request: Request) -> bool:
    """Browsers send `X-Auth-Mode: cookie`. The custom header also acts as a CSRF guard:
    a cross-site form or image request cannot set it."""
    return request.headers.get(AUTH_MODE_HEADER, "").lower() == "cookie"


def _set_refresh_cookie(response: Response, token: str) -> None:
    secure = settings.COOKIE_SECURE if settings.COOKIE_SECURE is not None else settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,          # JavaScript can never read it
        secure=secure,          # HTTPS only in production
        samesite="strict",      # never sent on cross-site requests
        path=COOKIE_PATH,       # only sent to the auth endpoints
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.REFRESH_COOKIE_NAME, path=COOKIE_PATH)



@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive access + refresh tokens",
)
async def login(
    request: Request,
    response: Response,
    db: DBDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    svc  = AuthService(db)
    user = await svc.authenticate_user(form_data.username, form_data.password)

    if not user:
        # Don't reveal whether it's a bad username or bad password
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials or account locked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    pwf = password_fingerprint(user.hashed_password)
    access_token = security.create_access_token(
        subject=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role.value,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        pwf=pwf,
    )
    refresh_token = security.create_refresh_token(
        subject=str(user.id),
        tenant_id=user.tenant_id,
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        pwf=pwf,
    )

    if _cookie_mode(request):
        _set_refresh_cookie(response, refresh_token)
        refresh_token = None

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Exchange a refresh token for a new access token",
)
async def refresh_token(
    request: Request,
    response: Response,
    db: DBDep,
    body: Optional[TokenRefresh] = None,
):
    cookie_mode = _cookie_mode(request)
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME) if cookie_mode else (body.refresh_token if body else None)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    # Verify not blacklisted
    if await security.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    try:
        payload = security.decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if not security.verify_token_type(payload, security.REFRESH_TOKEN_TYPE):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = parse_subject(payload)
    svc  = AuthService(db)
    user = await svc.get_user_by_id(user_id) if user_id is not None else None
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    # Rejects tokens issued before a password change, or to a different tenant
    if not claims_match_user(payload, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Rotate: revoke the old refresh token ATOMICALLY. Checking "is it revoked?" and revoking it
    # as two steps let two simultaneous requests both succeed. SET NX lets exactly one through.
    remaining = max(payload.get("exp", 0) - int(time.time()), 1)
    if not await security.consume_token(token, remaining):
        logger.warning("Refresh token reuse rejected for user=%s", user.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    pwf = password_fingerprint(user.hashed_password)
    new_access = security.create_access_token(
        subject=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role.value,
        pwf=pwf,
    )
    new_refresh = security.create_refresh_token(
        subject=str(user.id),
        tenant_id=user.tenant_id,
        pwf=pwf,
    )

    if cookie_mode:
        _set_refresh_cookie(response, new_refresh)
        new_refresh = None

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=dict,
    summary="Sign out: revoke the presented tokens and clear the session cookie",
)
async def logout(
    request: Request,
    response: Response,
    body: Optional[LogoutRequest] = None,
):
    """Revoke the tokens the caller presents and clear the session cookie.

    Deliberately NOT behind authentication: a user whose short-lived access token has expired
    must still be able to sign out (the refresh cookie is the credential that needs revoking),
    and it can only ever revoke tokens the caller already holds."""
    # Blacklist the access token from the Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]
        try:
            payload = security.decode_token(access_token)
            remaining = payload.get("exp", 0) - int(__import__("time").time())
            if remaining > 0:
                await security.blacklist_token(access_token, remaining)
        except Exception:
            pass

    # Blacklist the refresh token (from the httpOnly cookie in web mode, else from the body)
    cookie_mode = _cookie_mode(request)
    refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME) if cookie_mode else (body.refresh_token if body else None)
    if refresh:
        try:
            payload = security.decode_token(refresh)
            remaining = payload.get("exp", 0) - int(__import__("time").time())
            if remaining > 0:
                await security.blacklist_token(refresh, remaining)
        except Exception:
            pass
    if cookie_mode:
        _clear_refresh_cookie(response)

    return {"message": "Logged out successfully"}


@router.post(
    "/register",
    response_model=UserInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (admin-gated in production)",
)
async def register(user_create: UserCreate, db: DBDep):
    """
    Public registration. Role is restricted to viewer/clerk/manager
    by the UserCreate schema validator — admin cannot self-register.
    Disabled unless REGISTRATION_OPEN=true; otherwise an admin creates users via POST /users/.
    """
    if not settings.REGISTRATION_OPEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is disabled. Ask an administrator to create your account.",
        )
    svc = AuthService(db)

    try:
        # Use tenant_id=1 as default — multi-tenant onboarding handled separately
        user = await svc.create_user(user_create, tenant_id=1)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return user