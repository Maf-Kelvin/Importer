# app/models/item.py
import enum
from datetime import date
from sqlalchemy import (
    Boolean, Date, Float, ForeignKey, Index, Integer,
    String, Text, Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import SoftDeleteModel


class ItemCondition(str, enum.Enum):
    NEW     = "new"
    TOKUNBO = "tokunbo"
    USED    = "used"


class ItemCategory(str, enum.Enum):
    ELECTRONICS = "electronics"
    VEHICLES    = "vehicles"
    ENGINES     = "engines"
    APPLIANCES  = "appliances"
    FOOD_ITEMS  = "food_items"
    LAPTOPS     = "laptops"
    OTHER       = "other"


class Item(SoftDeleteModel):
    __tablename__ = "items"

    # Tenant
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    container_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Basic info
    name:        Mapped[str]      = mapped_column(String(255), nullable=False)
    description: Mapped[str|None] = mapped_column(Text, nullable=True)
    category:    Mapped[ItemCategory] = mapped_column(SQLEnum(ItemCategory), nullable=False)
    condition:   Mapped[ItemCondition] = mapped_column(SQLEnum(ItemCondition), nullable=False)

    # Purchase — date stored as proper Date column, not String
    purchase_price:    Mapped[float]    = mapped_column(Float, nullable=False)
    purchase_currency: Mapped[str]      = mapped_column(String(3), nullable=False)
    purchase_date:     Mapped[date|None] = mapped_column(Date, nullable=True)   # fixed: was String

    # FX
    fx_rate_to_usd:    Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    purchase_price_usd: Mapped[float] = mapped_column(Float, nullable=False)

    # Physical
    weight: Mapped[float]      = mapped_column(Float, nullable=False)
    volume: Mapped[float|None] = mapped_column(Float, nullable=True)

    # Cost allocation
    allocated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    landed_cost:    Mapped[float] = mapped_column(Float, default=0.0)

    # Pricing
    recommended_price: Mapped[float|None] = mapped_column(Float, nullable=True)
    selling_price:     Mapped[float|None] = mapped_column(Float, nullable=True)
    sold:              Mapped[bool]        = mapped_column(Boolean, default=False)
    sold_date:         Mapped[date|None]   = mapped_column(Date, nullable=True)   # fixed: was String

    # Full-text search vector (populated by trigger or service)
    extra_data: Mapped[dict|None] = mapped_column(JSONB, nullable=True)

    # Relationships
    container:     Mapped["Container"]       = relationship("Container",    back_populates="items")
    price_records: Mapped[list["PriceRecord"]] = relationship(
        "PriceRecord", back_populates="item", cascade="all, delete-orphan"
    )
    warehouse_inventory: Mapped[list["WarehouseInventory"]] = relationship(
        "WarehouseInventory", back_populates="item"
    )
    sale: Mapped["Sale|None"] = relationship("Sale", back_populates="item", uselist=False)

    __table_args__ = (
        Index("ix_item_tenant_category",  "tenant_id", "category"),
        Index("ix_item_tenant_sold",      "tenant_id", "sold"),
        Index("ix_item_container_id",     "container_id"),
    )

    def __repr__(self) -> str:
        return f"<Item id={self.id} name={self.name!r} category={self.category}>"