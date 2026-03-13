# app/models/pricing.py
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum as SQLEnum, DateTime, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import enum


class PricingMethod(str, enum.Enum):
    COST_BASED = "cost_based"
    MARKET_BASED = "market_based"
    LAST_SOLD = "last_sold"


class PricingSource(str, enum.Enum):
    JIJI = "jiji"
    EBAY = "ebay"
    MOBILE_DE = "mobile_de"
    AUTOSCOUT24 = "autoscout24"
    BAZOS_CZ = "bazos_cz"


class PriceRecord(BaseModel):
    __tablename__ = "price_records"
    
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Pricing details
    method = Column(SQLEnum(PricingMethod), nullable=False)
    source = Column(SQLEnum(PricingSource))
    price = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    # Market data (for market-based pricing)
    source_url = Column(String)
    source_data = Column(JSON)
    confidence_score = Column(Float)  # 0-1 confidence in market price
    
    # Cost-based data
    margin_percentage = Column(Float)
    
    # Metadata
    notes = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    item = relationship("Item", back_populates="price_records")
    user = relationship("User", back_populates="price_records")
