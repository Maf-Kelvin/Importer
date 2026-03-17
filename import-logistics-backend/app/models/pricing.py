# app/models/pricing.py
import enum
from sqlalchemy import (
    Boolean, Float, ForeignKey, Index, Integer,
    String, Text, Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import BaseModel


class PricingMethod(str, enum.Enum):
    COST_BASED   = "cost_based"
    MARKET_BASED = "market_based"
    LAST_SOLD    = "last_sold"


class PricingSource(str, enum.Enum):
    JIJI        = "jiji"
    EBAY        = "ebay"
    MOBILE_DE   = "mobile_de"
    AUTOSCOUT24 = "autoscout24"
    BAZOS_CZ    = "bazos_cz"


class PriceRecord(BaseModel):
    __tablename__ = "price_records"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False, index=True,
    )

    # Pricing details
    method:   Mapped[PricingMethod]    = mapped_column(SQLEnum(PricingMethod), nullable=False)
    source:   Mapped[PricingSource|None] = mapped_column(SQLEnum(PricingSource), nullable=True)
    price:    Mapped[float]            = mapped_column(Float, nullable=False)
    currency: Mapped[str]              = mapped_column(String(3), nullable=False, default="USD")

    # Market data
    source_url:       Mapped[str|None]   = mapped_column(Text, nullable=True)
    source_data:      Mapped[dict|None]  = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float|None] = mapped_column(Float, nullable=True)

    # Cost-based data
    margin_percentage: Mapped[float|None] = mapped_column(Float, nullable=True)

    # Status
    notes:     Mapped[str|None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool]     = mapped_column(Boolean, default=True, nullable=False)  # fixed: Boolean now imported

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="price_records")
    user: Mapped["User"] = relationship("User", back_populates="price_records")

    __table_args__ = (
        Index("ix_pricerecord_item_active", "item_id", "is_active"),
        Index("ix_pricerecord_tenant_id",   "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<PriceRecord id={self.id} item_id={self.item_id} price={self.price} method={self.method}>"