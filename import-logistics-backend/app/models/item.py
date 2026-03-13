# app/models/item.py
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class ItemCondition(str, enum.Enum):
    NEW = "new"
    TOKUNBO = "tokunbo"
    USED = "used"


class ItemCategory(str, enum.Enum):
    ELECTRONICS = "electronics"
    VEHICLES = "vehicles"
    ENGINES = "engines"
    APPLIANCES = "appliances"
    FOOD_ITEMS = "food_items"
    LAPTOPS = "laptops"
    OTHER = "other"


class Item(BaseModel):
    __tablename__ = "items"
    
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=False)
    
    # Basic info
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(SQLEnum(ItemCategory), nullable=False)
    condition = Column(SQLEnum(ItemCondition), nullable=False)
    
    # Purchase details
    purchase_price = Column(Float, nullable=False)
    purchase_currency = Column(String(3), nullable=False)
    purchase_date = Column(String)  # Store as string for flexibility
    
    # FX tracking
    fx_rate_to_usd = Column(Float, nullable=False, default=1.0)
    purchase_price_usd = Column(Float, nullable=False)
    
    # Physical properties
    weight = Column(Float, nullable=False)  # in kg
    volume = Column(Float)  # in cubic meters, optional
    
    # Cost allocation
    allocated_cost = Column(Float, default=0.0)
    landed_cost = Column(Float, default=0.0)  # purchase_price + allocated_cost
    
    # Pricing
    recommended_price = Column(Float)
    selling_price = Column(Float)
    sold = Column(Boolean, default=False)
    sold_date = Column(String)
    
    # Additional data
    metadata = Column(JSON)
    
    # Relationships
    container = relationship("Container", back_populates="items")
    price_records = relationship("PriceRecord", back_populates="item", cascade="all, delete-orphan")

