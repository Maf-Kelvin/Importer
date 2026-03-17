# app/schemas/user.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.models.user import UserRole


# ------------------------------------------------------------------------------
# User
# ------------------------------------------------------------------------------
class UserBase(BaseModel):
    email:      EmailStr
    username:   str
    first_name: str
    last_name:  str
    is_active:  bool = True


class UserCreate(UserBase):
    password: str
    # Role defaults to VIEWER. ADMIN cannot be self-assigned —
    # admin creation is restricted to the admin-only POST /users/ endpoint.
    role: UserRole = UserRole.VIEWER

    @field_validator("role")
    @classmethod
    def restrict_self_register_role(cls, v: UserRole) -> UserRole:
        # This schema is used for public /register endpoint.
        # Clerk, manager, viewer are fine; admin is not.
        if v == UserRole.ADMIN:
            raise ValueError("Cannot self-register as admin")
        return v


class UserAdminCreate(UserBase):
    """Admin-only creation schema — any role allowed."""
    password: str
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    email:      Optional[EmailStr] = None
    username:   Optional[str]      = None
    first_name: Optional[str]      = None
    last_name:  Optional[str]      = None
    password:   Optional[str]      = None
    # Users cannot change their own role — handled in router


class UserAdminUpdate(UserUpdate):
    """Admin can additionally update role and is_active."""
    role:      Optional[UserRole] = None
    is_active: Optional[bool]     = None


class UserInDB(UserBase):
    id:           int
    role:         UserRole
    is_superuser: bool
    tenant_id:    int
    last_login:   Optional[datetime] = None
    created_at:   datetime
    updated_at:   datetime

    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    """Minimal user info safe to embed in other responses."""
    id:         int
    username:   str
    first_name: str
    last_name:  str
    role:       UserRole

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------------------
# Auth tokens
# ------------------------------------------------------------------------------
class Token(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int          # access token TTL in seconds


class TokenRefresh(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str          # also blacklist the refresh token on logout


class TokenPayload(BaseModel):
    sub:       str
    tenant_id: int
    role:      str
    type:      str