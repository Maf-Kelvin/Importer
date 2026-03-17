# app/models/analytics.py
import enum
from datetime import date, datetime
from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey,
    Index, Integer, Numeric, String, Text, UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import BaseModel


# ==============================================================================
# Exchange Rate History
# ==============================================================================
class ExchangeRateHistory(BaseModel):
    __tablename__ = "exchange_rate_history"

    from_currency: Mapped[str]   = mapped_column(String(3), nullable=False)
    to_currency:   Mapped[str]   = mapped_column(String(3), nullable=False)
    rate:          Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    date:          Mapped[date]  = mapped_column(Date, nullable=False)
    source:        Mapped[str|None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", "date", name="uq_fx_rate_date"),
        Index("ix_fx_from_to_date", "from_currency", "to_currency", "date"),
    )

    def __repr__(self) -> str:
        return f"<ExchangeRateHistory {self.from_currency}→{self.to_currency} {self.rate} on {self.date}>"


# ==============================================================================
# Notifications
# ==============================================================================
class NotificationType(str, enum.Enum):
    TRACKING_UPDATE  = "tracking_update"
    PRICE_CHANGE     = "price_change"
    LOW_STOCK        = "low_stock"
    CONTAINER_ARRIVED = "container_arrived"
    PAYMENT_RECEIVED = "payment_received"
    SYSTEM           = "system"


class Notification(BaseModel):
    __tablename__ = "notifications"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType), nullable=False
    )
    title:   Mapped[str]      = mapped_column(String(255), nullable=False)
    message: Mapped[str]      = mapped_column(Text, nullable=False)
    read:    Mapped[bool]     = mapped_column(Boolean, default=False)
    data:    Mapped[dict|None] = mapped_column(JSONB, nullable=True)  # extra context

    organization: Mapped["Organization"] = relationship("Organization", back_populates="notifications")
    user:         Mapped["User"]         = relationship("User",         back_populates="notifications")

    __table_args__ = (
        Index("ix_notification_user_read", "user_id", "read"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} type={self.notification_type} read={self.read}>"


# ==============================================================================
# Audit Logs
# ==============================================================================
class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[int|None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    action:      Mapped[str]       = mapped_column(String(100), nullable=False)  # e.g. "item.sold"
    entity_type: Mapped[str|None]  = mapped_column(String(100), nullable=True)   # e.g. "Item"
    entity_id:   Mapped[int|None]  = mapped_column(Integer,     nullable=True)
    ip_address:  Mapped[str|None]  = mapped_column(String(45),  nullable=True)
    user_agent:  Mapped[str|None]  = mapped_column(String(512), nullable=True)
    extra_data:  Mapped[dict|None] = mapped_column(JSONB, nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="audit_logs")
    user:         Mapped["User|None"]    = relationship("User",         back_populates="audit_logs")

    __table_args__ = (
        Index("ix_auditlog_tenant_action",    "tenant_id", "action"),
        Index("ix_auditlog_tenant_entity",    "tenant_id", "entity_type", "entity_id"),
        Index("ix_auditlog_created_at",       "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r} entity={self.entity_type}:{self.entity_id}>"


# ==============================================================================
# Demand Analytics
# ==============================================================================
class DemandAnalytics(BaseModel):
    __tablename__ = "demand_analytics"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    item_category:    Mapped[str]        = mapped_column(String(100), nullable=False)
    avg_market_price: Mapped[float|None] = mapped_column(Numeric(14, 2), nullable=True)
    avg_sale_price:   Mapped[float|None] = mapped_column(Numeric(14, 2), nullable=True)
    avg_margin:       Mapped[float|None] = mapped_column(Float, nullable=True)
    demand_score:     Mapped[float|None] = mapped_column(Float, nullable=True)  # 0-100
    units_sold_30d:   Mapped[int]        = mapped_column(Integer, default=0)
    units_sold_90d:   Mapped[int]        = mapped_column(Integer, default=0)
    updated_at_calc:  Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_data:       Mapped[dict|None]  = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "item_category", name="uq_demand_tenant_category"),
        Index("ix_demand_tenant_category", "tenant_id", "item_category"),
    )

    def __repr__(self) -> str:
        return f"<DemandAnalytics tenant={self.tenant_id} category={self.item_category!r} score={self.demand_score}>"