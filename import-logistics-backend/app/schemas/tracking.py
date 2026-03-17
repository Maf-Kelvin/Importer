# app/schemas/tracking.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field   # Field was missing — now imported

from app.models.tracking import TrackingStatus


class TrackingRecordBase(BaseModel):
    container_id:  int
    status:        TrackingStatus
    location:      Optional[str] = None
    vessel_name:   Optional[str] = None
    voyage_number: Optional[str] = None


class TrackingRecordInDB(TrackingRecordBase):
    id:                int
    tenant_id:         int
    status_date:       Optional[datetime] = None   # fixed: was str
    estimated_arrival: Optional[datetime] = None   # fixed: was str
    actual_arrival:    Optional[datetime] = None
    notification_sent: bool
    created_at:        datetime           # fixed: was str
    updated_at:        datetime           # fixed: was str

    model_config = ConfigDict(from_attributes=True)


class NotificationSettingsUpdate(BaseModel):
    enable_notifications:  bool = True
    notification_interval: int  = Field(3, ge=1, le=7)   # days — Field now imported
    email_notifications:   bool = True
    webhook_url:           Optional[str] = None


class TrackingStatusResponse(BaseModel):
    status:            str
    location:          Optional[str]     = None
    vessel_name:       Optional[str]     = None
    voyage_number:     Optional[str]     = None
    status_date:       Optional[datetime] = None
    estimated_arrival: Optional[datetime] = None
    last_updated:      datetime