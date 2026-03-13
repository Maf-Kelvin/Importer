# app/models/tracking.py
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SQLEnum, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import enum


class TrackingStatus(str, enum.Enum):
    BOOKED = "booked"
    GATE_IN = "gate_in"
    LOADED = "loaded"
    DEPARTED = "departed"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    DISCHARGED = "discharged"
    GATE_OUT = "gate_out"
    DELIVERED = "delivered"


class TrackingRecord(BaseModel):
    __tablename__ = "tracking_records"
    
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=False)
    
    # Tracking details
    status = Column(SQLEnum(TrackingStatus), nullable=False)
    location = Column(String)
    vessel_name = Column(String)
    voyage_number = Column(String)
    
    # Timestamps
    status_date = Column(DateTime)
    estimated_arrival = Column(DateTime)
    actual_arrival = Column(DateTime)
    
    # Raw API response
    raw_data = Column(JSON)
    
    # Notification settings
    notification_sent = Column(Boolean, default=False)
    
    # Relationships
    container = relationship("Container", back_populates="tracking_records")