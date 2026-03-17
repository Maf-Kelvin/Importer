# app/models/tracking.py
import enum
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer,
    String, Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import BaseModel


class TrackingStatus(str, enum.Enum):
    BOOKED     = "booked"
    GATE_IN    = "gate_in"
    LOADED     = "loaded"
    DEPARTED   = "departed"
    IN_TRANSIT = "in_transit"
    ARRIVED    = "arrived"
    DISCHARGED = "discharged"
    GATE_OUT   = "gate_out"
    DELIVERED  = "delivered"
    UNKNOWN    = "unknown"          # safe fallback — was crashing before


class TrackingRecord(BaseModel):
    __tablename__ = "tracking_records"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    container_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Status
    status:         Mapped[TrackingStatus] = mapped_column(SQLEnum(TrackingStatus), nullable=False)
    location:       Mapped[str|None]       = mapped_column(String(255), nullable=True)
    vessel_name:    Mapped[str|None]       = mapped_column(String(255), nullable=True)
    voyage_number:  Mapped[str|None]       = mapped_column(String(100), nullable=True)

    # Timestamps
    status_date:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_arrival: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival:    Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Raw API response
    raw_data: Mapped[dict|None] = mapped_column(JSONB, nullable=True)

    # Notifications
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    container: Mapped["Container"] = relationship("Container", back_populates="tracking_records")

    __table_args__ = (
        # Composite index — most tracking queries filter by container + status
        Index("ix_tracking_container_status", "container_id", "status"),
        Index("ix_tracking_tenant_id",        "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<TrackingRecord id={self.id} container_id={self.container_id} status={self.status}>"