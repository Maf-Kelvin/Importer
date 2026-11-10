# app/schemas/pricing.py
# NOTE: This file must NOT import from app.schemas.item to avoid circular imports.
# ItemWithPricing in item.py uses TYPE_CHECKING to import PriceRecordInDB.
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.pricing import PricingMethod, PricingSource
from app.schemas.types import Money, PositiveMoney


# ------------------------------------------------------------------------------
# Price Record
# ------------------------------------------------------------------------------
class PriceRecordBase(BaseModel):
    item_id:           int
    method:            PricingMethod
    price:             PositiveMoney
    currency:          str   = Field(..., min_length=3, max_length=3)
    source:            Optional[PricingSource] = None
    margin_percentage: Optional[float]         = None
    notes:             Optional[str]           = None


class PriceRecordCreate(PriceRecordBase):
    pass


class PriceRecordInDB(PriceRecordBase):
    id:               int
    user_id:          int
    tenant_id:        int
    source_url:       Optional[str]   = None
    confidence_score: Optional[float] = None
    is_active:        bool
    created_at:       datetime
    updated_at:       datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------------------
# Pricing request / response
# ------------------------------------------------------------------------------
class PricingRequest(BaseModel):
    include_cost_based:    bool = True
    include_market_pricing: bool = True
    include_last_sold:     bool = True
    profit_margin:         Optional[float] = Field(None, ge=0.05, le=1.0)
    sources:               Optional[List[PricingSource]] = None


class MarketPrice(BaseModel):
    source:     PricingSource
    price:      Money
    currency:   str
    url:        Optional[str]   = None
    confidence: float
    found_at:   datetime
    price_usd:  Optional[Money] = None    # converted to USD for comparison
    age_days:   Optional[float] = None


class PricingResponse(BaseModel):
    item_id:            int
    cost_based_price:   Optional[Money]       = None
    market_prices:      List[MarketPrice]     = []
    last_sold_price:    Optional[Money]       = None
    recommended_price:  Optional[Money]       = None
    profit_margin:      Optional[float]       = None
    landed_cost:        Optional[Money]       = None
    generated_at:       datetime
    # --- explainable recommendation ---
    price_low:          Optional[Money]       = None   # suggested band (low)
    price_high:         Optional[Money]       = None   # suggested band (high)
    confidence:         Optional[float]       = None   # 0..1, how much to trust the market signal
    expected_margin:    Optional[float]       = None   # (recommended - cost) / cost
    comparables_used:   int                   = 0
    warnings:           List[str]             = []
    explanation:        List[str]             = []


class PricingAccuracy(BaseModel):
    """How close our recommendations were to what items actually sold for."""
    n:            int
    mape:         float   # mean absolute percentage error (lower is better)
    bias:         float   # + = we recommend too high, - = too low
    within_10pct: float   # share of sales within 10% of the recommendation