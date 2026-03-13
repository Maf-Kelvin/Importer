# app/schemas/item.py
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.item import ItemCondition, ItemCategory
from app.schemas.pricing import PriceRecordInDB


class ItemBase(BaseModel):
    container_id: int
    name: str
    description: Optional[str] = None
    category: ItemCategory
    condition: ItemCondition
    purchase_price: float = Field(..., gt=0)
    purchase_currency: str = Field(..., min_length=3, max_length=3)
    purchase_date: Optional[str] = None
    weight: float = Field(..., gt=0)
    volume: Optional[float] = Field(None, gt=0)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ItemCategory] = None
    condition: Optional[ItemCondition] = None
    purchase_price: Optional[float] = Field(None, gt=0)
    purchase_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    purchase_date: Optional[str] = None
    weight: Optional[float] = Field(None, gt=0)
    volume: Optional[float] = Field(None, gt=0)
    selling_price: Optional[float] = Field(None, gt=0)


class ItemInDB(ItemBase):
    id: int
    fx_rate_to_usd: float
    purchase_price_usd: float
    allocated_cost: float
    landed_cost: float
    recommended_price: Optional[float] = None
    selling_price: Optional[float] = None
    sold: bool
    sold_date: Optional[str] = None
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ItemWithPricing(ItemInDB):
    price_records: List[PriceRecordInDB]
    profit_margin: Optional[float] = None
    profit_amount: Optional[float] = None