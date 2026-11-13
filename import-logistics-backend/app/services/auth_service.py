# app/services/auth_service.py
import logging
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import transaction
from app.core.security import (
    verify_password,
    get_password_hash,
    is_account_locked,
    record_failed_login,
    clear_failed_logins,
    login_lock_key,
)
from app.core import request_context
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserAdminCreate

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    async def authenticate_user(
        self, username: str, password: str
    ) -> Optional[User]:
        """
        Authenticate user. Returns None on failure.
        Enforces account lockout after MAX_LOGIN_ATTEMPTS failures.
        Updates last_login on success.
        """
        # Lockout is per (username, client IP), so strangers cannot lock a user out
        lock_key = login_lock_key(username, request_context.client_ip.get())

        # Check lockout before any DB query
        if await is_account_locked(lock_key):
            logger.warning("Locked account login attempt: %s", username)
            return None

        user = await self.get_user_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            count = await record_failed_login(lock_key)
            logger.warning(
                "Failed login attempt %d for username=%s", count, username
            )
            return None

        # Success — reset counter and update last_login
        await clear_failed_logins(lock_key)
        async with transaction(self.db):
            user.last_login = datetime.now(UTC)
            user.failed_login_attempts = 0
        logger.info("Successful login: user_id=%d username=%s", user.id, username)
        return user

    # ------------------------------------------------------------------
    # User creation
    # ------------------------------------------------------------------
    async def create_user(
        self,
        user_data: UserCreate | UserAdminCreate,
        tenant_id: int,
    ) -> User:
        """
        Create a new user. Raises ValueError on duplicate email/username.
        Wrapped in a transaction so partial writes never persist.
        """
        # Duplicate checks before opening transaction
        if await self.get_user_by_email(user_data.email):
            raise ValueError(f"Email already registered: {user_data.email}")
        if await self.get_user_by_username(user_data.username):
            raise ValueError(f"Username already taken: {user_data.username}")

        async with transaction(self.db):
            user = User(
                tenant_id=tenant_id,
                email=user_data.email,
                username=user_data.username,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                role=user_data.role,
                hashed_password=get_password_hash(user_data.password),
                is_active=user_data.is_active,
            )
            self.db.add(user)

        await self.db.refresh(user)
        logger.info("User created: user_id=%d username=%s", user.id, user.username)
        return user

    # ------------------------------------------------------------------
    # User update
    # ------------------------------------------------------------------
    async def update_user(
        self,
        user: User,
        update_data: dict,
    ) -> User:
        # email and username are unique across the platform: report a clash as a conflict (409), not a crash
        for field in ("email", "username"):
            value = update_data.get(field)
            if value is not None and value != getattr(user, field):
                taken = (
                    await self.db.execute(
                        select(User.id).where(getattr(User, field) == value, User.id != user.id)
                    )
                ).first()
                if taken:
                    raise ValueError(f"That {field} is already in use")
        async with transaction(self.db):
            for field, value in update_data.items():
                if field == "password" and value:
                    user.hashed_password = get_password_hash(value)
                elif field != "password":
                    setattr(user, field, value)

        await self.db.refresh(user)
        return user