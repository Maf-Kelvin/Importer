# app/models/user.py
import enum
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index,
    Integer, String, Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    ADMIN   = "admin"
    MANAGER = "manager"
    CLERK   = "clerk"
    VIEWER  = "viewer"


class User(BaseModel):
    __tablename__ = "users"

    # Tenant
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Identity
    email:    Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name:  Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Status & role
    is_active:    Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False
    )

    # Audit / security
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int]  = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization:  Mapped["Organization"]     = relationship("Organization", back_populates="users")
    containers:    Mapped[list["Container"]]  = relationship("Container",  back_populates="owner")
    price_records: Mapped[list["PriceRecord"]] = relationship("PriceRecord", back_populates="user")
    audit_logs:    Mapped[list["AuditLog"]]   = relationship("AuditLog",   back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")
    orders:        Mapped[list["Order"]]      = relationship("Order",      back_populates="created_by")

    __table_args__ = (
        Index("ix_users_tenant_email", "tenant_id", "email"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"