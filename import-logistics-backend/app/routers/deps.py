# app/routers/deps.py
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.database import get_db
from app.models.user import User, UserRole

# Re-export get_db so routers can import from one place
__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_admin_user",
    "get_manager_or_admin_user",
    "get_clerk_or_higher_user",
    "DBDep",
    "CurrentUser",
]

security_scheme = HTTPBearer()

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> User:
    token = credentials.credentials

    # 1. Check blacklist first — fast Redis lookup
    if await security.is_token_blacklisted(token):
        raise _CREDENTIALS_EXC

    # 2. Decode & validate JWT
    try:
        payload = security.decode_token(token)
    except JWTError:
        raise _CREDENTIALS_EXC

    # 3. Ensure it's an access token, not a refresh token
    if not security.verify_token_type(payload, security.ACCESS_TOKEN_TYPE):
        raise _CREDENTIALS_EXC

    username: str | None = payload.get("sub")
    if not username:
        raise _CREDENTIALS_EXC

    # 4. Load user from DB
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise _CREDENTIALS_EXC

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != UserRole.ADMIN and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_manager_or_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if (
        current_user.role not in (UserRole.ADMIN, UserRole.MANAGER)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or admin access required",
        )
    return current_user


async def get_clerk_or_higher_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if (
        current_user.role not in (UserRole.ADMIN, UserRole.MANAGER, UserRole.CLERK)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clerk access or higher required",
        )
    return current_user


# ------------------------------------------------------------------------------
# Typed shortcuts — use these in router signatures for cleaner code
# e.g.  async def my_route(db: DBDep, user: CurrentUser): ...
# ------------------------------------------------------------------------------
DBDep      = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser   = Annotated[User, Depends(get_admin_user)]
ManagerUser = Annotated[User, Depends(get_manager_or_admin_user)]
ClerkUser   = Annotated[User, Depends(get_clerk_or_higher_user)]