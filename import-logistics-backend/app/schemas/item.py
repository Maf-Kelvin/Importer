# app/schemas/item.py
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.item import ItemCategory, ItemCondition

# Break circular import — PriceRecordInDB only imported for type hints
if TYPE_CHECKING:
    from app.schemas.pricing import PriceRecordInDB


# ------------------------------------------------------------------------------
# Item
# ------------------------------------------------------------------------------
class ItemBase(BaseModel):
    container_id:      int
    name:              str
    description:       Optional[str]       = None
    category:          ItemCategory
    condition:         ItemCondition
    purchase_price:    float               = Field(..., gt=0)
    purchase_currency: str                 = Field(..., min_length=3, max_length=3)
    purchase_date:     Optional[date]      = None   # fixed: was Optional[str]
    weight:            float               = Field(..., gt=0, description="Weight in kg")
    volume:            Optional[float]     = Field(None, gt=0, description="Volume in m³")


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name:              Optional[str]          = None
    description:       Optional[str]          = None
    category:          Optional[ItemCategory] = None
    condition:         Optional[ItemCondition] = None
    purchase_price:    Optional[float]        = Field(None, gt=0)
    purchase_currency: Optional[str]          = Field(None, min_length=3, max_length=3)
    purchase_date:     Optional[date]         = None
    weight:            Optional[float]        = Field(None, gt=0)
    volume:            Optional[float]        = Field(None, gt=0)
    selling_price:     Optional[float]        = Field(None, gt=0)


class MarkSoldRequest(BaseModel):
    """Request body for POST /items/{id}/mark-sold — not a query param."""
    selling_price: float = Field(..., gt=0)
    sold_date:     Optional[date] = None
    customer_id:   Optional[int]  = None
    notes:         Optional[str]  = None


class ItemInDB(ItemBase):
    id:                 int
    tenant_id:          int
    fx_rate_to_usd:     float
    purchase_price_usd: float
    allocated_cost:     float
    landed_cost:        float
    recommended_price:  Optional[float] = None
    selling_price:      Optional[float] = None
    sold:               bool
    sold_date:          Optional[date]  = None   # fixed: was Optional[str]
    created_at:         datetime
    updated_at:         datetime
    deleted_at:         Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ItemWithPricing(ItemInDB):
    price_records:  List["PriceRecordInDB"] = []
    profit_margin:  Optional[float]         = None
    profit_amount:  Optional[float]         = None

    model_config = ConfigDict(from_attributes=True)


# Resolve forward reference
ItemWithPricing.model_rebuild()