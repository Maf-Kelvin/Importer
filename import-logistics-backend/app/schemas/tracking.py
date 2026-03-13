# app/schemas/tracking.py
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.models.tracking import TrackingStatus


class TrackingRecordBase(BaseModel):
    container_id: int
    status: TrackingStatus
    location: Optional[str] = None
    vessel_name: Optional[str] = None
    voyage_number: Optional[str] = None


class TrackingRecordInDB(TrackingRecordBase):
    id: int
    status_date: Optional[str] = None
    estimated_arrival: Optional[str] = None
    actual_arrival: Optional[str] = None
    notification_sent: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class NotificationSettingsUpdate(BaseModel):
    enable_notifications: bool = True
    notification_interval: int = Field(3, ge=1, le=7)  # days
    email_notifications: bool = True
    webhook_url: Optional[str] = None