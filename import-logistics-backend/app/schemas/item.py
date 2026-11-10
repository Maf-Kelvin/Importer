
# app/schemas/item.py

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.item import ItemCategory, ItemCondition
from app.schemas.types import Money, PositiveMoney, Rate, Weight
from app.schemas.pricing import PriceRecordInDB


# ------------------------------------------------------------------------------
# Item
# ------------------------------------------------------------------------------

class ItemBase(BaseModel):
    container_id: int
    name: str
    description: Optional[str] = None
    category: ItemCategory
    condition: ItemCondition
    purchase_price: PositiveMoney
    purchase_currency: str = Field(..., min_length=3, max_length=3)
    purchase_date: Optional[date] = None
    weight: Weight
    volume: Optional[Weight] = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ItemCategory] = None
    condition: Optional[ItemCondition] = None
    purchase_price: Optional[PositiveMoney] = None
    purchase_currency: Optional[str] = Field(
        None, min_length=3, max_length=3
    )
    purchase_date: Optional[date] = None
    weight: Optional[Weight] = None
    volume: Optional[Weight] = None
    selling_price: Optional[PositiveMoney] = None


class MarkSoldRequest(BaseModel):
    """Request body for POST /items/{id}/mark-sold."""
    selling_price: PositiveMoney
    sold_date: Optional[date] = None
    customer_id: Optional[int] = None
    notes: Optional[str] = None


class ItemInDB(ItemBase):
    id: int
    tenant_id: int
    fx_rate_to_usd: Rate
    purchase_price_usd: Money
    allocated_cost: Money
    landed_cost: Money
    recommended_price: Optional[Money] = None
    selling_price: Optional[Money] = None
    sold: bool
    sold_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ItemWithPricing(ItemInDB):
    price_records: List[PriceRecordInDB] = Field(
        default_factory=list
    )
    profit_margin: Optional[float] = None
    profit_amount: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------------------
# Resolve Pydantic schema references
# ------------------------------------------------------------------------------

ItemWithPricing.model_rebuild()
