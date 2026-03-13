# app/schemas/pricing.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.pricing import PricingMethod, PricingSource


class PriceRecordBase(BaseModel):
    item_id: int
    method: PricingMethod
    price: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    source: Optional[PricingSource] = None
    margin_percentage: Optional[float] = None
    notes: Optional[str] = None


class PriceRecordCreate(PriceRecordBase):
    pass


class PriceRecordInDB(PriceRecordBase):
    id: int
    user_id: int
    source_url: Optional[str] = None
    confidence_score: Optional[float] = None
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class PricingRequest(BaseModel):
    include_cost_based: bool = True
    include_market_pricing: bool = True
    include_last_sold: bool = True
    profit_margin: Optional[float] = Field(None, ge=0.05, le=1.0)
    sources: Optional[List[PricingSource]] = None


class MarketPrice(BaseModel):
    source: PricingSource
    price: float
    currency: str
    url: Optional[str] = None
    confidence: float
    found_at: str


class PricingResponse(BaseModel):
    item_id: int
    cost_based_price: Optional[float] = None
    market_prices: List[MarketPrice] = []
    last_sold_price: Optional[float] = None
    recommended_price: Optional[float] = None
    profit_margin: Optional[float] = None
    generated_at: str
