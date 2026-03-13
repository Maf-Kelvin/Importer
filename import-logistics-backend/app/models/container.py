# app/models/container.py
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.core.config import CONTAINER_TYPES, ALLOCATION_METHODS
import enum


class ContainerType(str, enum.Enum):
    TWENTY_FT = "20ft"
    FORTY_FT = "40ft"


class AllocationMethod(str, enum.Enum):
    WEIGHT_BASED = "weight_based"
    VALUE_BASED = "value_based"


class Container(BaseModel):
    __tablename__ = "containers"
    
    name = Column(String, nullable=False)
    container_type = Column(SQLEnum(ContainerType), nullable=False)
    msc_container_number = Column(String, unique=True, index=True)
    
    # Allocation settings
    allocation_method = Column(SQLEnum(AllocationMethod), default=AllocationMethod.WEIGHT_BASED)
    allocation_override = Column(Boolean, default=False)
    
    # Status
    is_sealed = Column(Boolean, default=False)
    is_shipped = Column(Boolean, default=False)
    
    # Owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Additional metadata
    notes = Column(String)
    metadata = Column(JSON)
    
    # Relationships
    owner = relationship("User", back_populates="containers")
    expenses = relationship("ContainerExpense", back_populates="container", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="container", cascade="all, delete-orphan")
    tracking_records = relationship("TrackingRecord", back_populates="container", cascade="all, delete-orphan")
