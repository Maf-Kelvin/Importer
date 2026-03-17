# app/routers/auth.py
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
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


@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive access + refresh tokens",
)
async def login(
    request: Request,
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

    access_token = security.create_access_token(
        subject=user.username,
        tenant_id=user.tenant_id,
        role=user.role.value,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = security.create_refresh_token(
        subject=user.username,
        tenant_id=user.tenant_id,
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )

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
async def refresh_token(body: TokenRefresh, db: DBDep):
    # Verify not blacklisted
    if await security.is_token_blacklisted(body.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    try:
        payload = security.decode_token(body.refresh_token)
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

    username: str = payload.get("sub", "")
    tenant_id: int = payload.get("tenant_id", 0)

    svc  = AuthService(db)
    user = await svc.get_user_by_username(username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Rotate — blacklist old refresh token
    remaining = payload.get("exp", 0) - int(__import__("time").time())
    if remaining > 0:
        await security.blacklist_token(body.refresh_token, remaining)

    new_access = security.create_access_token(
        subject=user.username,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    new_refresh = security.create_refresh_token(
        subject=user.username,
        tenant_id=user.tenant_id,
    )

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=dict,
    summary="Revoke access + refresh tokens",
)
async def logout(
    request: Request,
    body: LogoutRequest,
    current_user=Depends(get_current_active_user),
):
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

    # Blacklist the refresh token
    try:
        payload = security.decode_token(body.refresh_token)
        remaining = payload.get("exp", 0) - int(__import__("time").time())
        if remaining > 0:
            await security.blacklist_token(body.refresh_token, remaining)
    except Exception:
        pass

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
    In production, set REGISTRATION_OPEN=false and use admin POST /users/.
    """
    svc = AuthService(db)

    try:
        # Use tenant_id=1 as default — multi-tenant onboarding handled separately
        user = await svc.create_user(user_create, tenant_id=1)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return user