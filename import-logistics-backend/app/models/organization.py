# app/models/organization.py
from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import BaseModel


class Organization(BaseModel):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Subscription / plan info (Phase 2 Stripe integration hooks)
    plan: Mapped[str] = mapped_column(String(50), default="starter", nullable=False)
    max_users: Mapped[int] = mapped_column(default=5, nullable=False)
    max_containers: Mapped[int] = mapped_column(default=50, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    containers: Mapped[list["Container"]] = relationship("Container", back_populates="organization")
    warehouses: Mapped[list["Warehouse"]] = relationship("Warehouse", back_populates="organization")
    customers: Mapped[list["Customer"]] = relationship("Customer", back_populates="organization")
    suppliers: Mapped[list["Supplier"]] = relationship("Supplier", back_populates="organization")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="organization")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="organization")

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r}>"