# app/models/logistics.py
import enum
from datetime import datetime
from sqlalchemy import (
    DateTime, Float, ForeignKey, Index, Integer,
    Numeric, String, Text, Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import BaseModel


# ==============================================================================
# Shipments
# ==============================================================================
class ShipmentStatus(str, enum.Enum):
    BOOKED     = "booked"
    IN_TRANSIT = "in_transit"
    ARRIVED    = "arrived"
    DELIVERED  = "delivered"
    DELAYED    = "delayed"


class Shipment(BaseModel):
    __tablename__ = "shipments"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    container_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    shipment_number:  Mapped[str]            = mapped_column(String(100), unique=True, nullable=False)
    carrier:          Mapped[str|None]        = mapped_column(String(100), nullable=True)
    tracking_number:  Mapped[str|None]        = mapped_column(String(100), nullable=True)
    origin_port:      Mapped[str|None]        = mapped_column(String(100), nullable=True)
    destination_port: Mapped[str|None]        = mapped_column(String(100), nullable=True)
    departure_date:   Mapped[datetime|None]   = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_date:     Mapped[datetime|None]   = mapped_column(DateTime(timezone=True), nullable=True)
    eta:              Mapped[datetime|None]   = mapped_column(DateTime(timezone=True), nullable=True)
    status:           Mapped[ShipmentStatus]  = mapped_column(
        SQLEnum(ShipmentStatus), default=ShipmentStatus.BOOKED, nullable=False
    )
    extra_data: Mapped[dict|None] = mapped_column(JSONB, nullable=True)

    container:      Mapped["Container"]        = relationship("Container", back_populates="shipments")
    transport_legs: Mapped[list["TransportLeg"]] = relationship("TransportLeg", back_populates="shipment")

    def __repr__(self) -> str:
        return f"<Shipment id={self.id} number={self.shipment_number!r} status={self.status}>"


# ==============================================================================
# Ports
# ==============================================================================
class Port(BaseModel):
    __tablename__ = "ports"

    port_name:  Mapped[str]        = mapped_column(String(255), nullable=False)
    country:    Mapped[str]        = mapped_column(String(100), nullable=False)
    port_code:  Mapped[str]        = mapped_column(String(10), unique=True, index=True, nullable=False)
    latitude:   Mapped[float|None] = mapped_column(Float, nullable=True)
    longitude:  Mapped[float|None] = mapped_column(Float, nullable=True)
    is_active:  Mapped[bool]       = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Port id={self.id} code={self.port_code!r} country={self.country!r}>"


# ==============================================================================
# Transport Legs
# ==============================================================================
class TransportType(str, enum.Enum):
    SEA   = "sea"
    AIR   = "air"
    ROAD  = "road"
    RAIL  = "rail"


class TransportLeg(BaseModel):
    __tablename__ = "transport_legs"

    container_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    shipment_id: Mapped[int|None] = mapped_column(
        Integer, ForeignKey("shipments.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    from_port:      Mapped[str]             = mapped_column(String(100), nullable=False)
    to_port:        Mapped[str]             = mapped_column(String(100), nullable=False)
    transport_type: Mapped[TransportType]   = mapped_column(SQLEnum(TransportType), nullable=False)
    departure_time: Mapped[datetime|None]   = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_time:   Mapped[datetime|None]   = mapped_column(DateTime(timezone=True), nullable=True)
    carrier:        Mapped[str|None]        = mapped_column(String(100), nullable=True)
    notes:          Mapped[str|None]        = mapped_column(Text, nullable=True)

    container: Mapped["Container"] = relationship("Container", back_populates="transport_legs")
    shipment:  Mapped["Shipment|None"] = relationship("Shipment", back_populates="transport_legs")

    def __repr__(self) -> str:
        return f"<TransportLeg id={self.id} {self.from_port}→{self.to_port}>"


# ==============================================================================
# Documents
# ==============================================================================
class DocumentType(str, enum.Enum):
    BILL_OF_LADING    = "bill_of_lading"
    CUSTOMS_FORM      = "customs_form"
    INVOICE           = "invoice"
    INSPECTION_REPORT = "inspection_report"
    PACKING_LIST      = "packing_list"
    INSURANCE         = "insurance"
    OTHER             = "other"


class Document(BaseModel):
    __tablename__ = "documents"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    container_id: Mapped[int|None] = mapped_column(
        Integer, ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    uploaded_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    document_type: Mapped[DocumentType] = mapped_column(SQLEnum(DocumentType), nullable=False)
    file_name:     Mapped[str]           = mapped_column(String(255), nullable=False)
    file_url:      Mapped[str]           = mapped_column(Text, nullable=False)
    file_size:     Mapped[int]           = mapped_column(Integer, nullable=False)
    mime_type:     Mapped[str]           = mapped_column(String(100), nullable=False)
    notes:         Mapped[str|None]      = mapped_column(Text, nullable=True)

    container: Mapped["Container|None"] = relationship("Container", back_populates="documents")

    __table_args__ = (
        Index("ix_document_tenant_container", "tenant_id", "container_id"),
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} type={self.document_type} file={self.file_name!r}>"


# ==============================================================================
# Customs Clearance
# ==============================================================================
class ClearanceStatus(str, enum.Enum):
    PENDING   = "pending"
    IN_REVIEW = "in_review"
    CLEARED   = "cleared"
    HELD      = "held"
    REJECTED  = "rejected"


class CustomsClearance(BaseModel):
    __tablename__ = "customs_clearance"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    container_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    clearance_status: Mapped[ClearanceStatus] = mapped_column(
        SQLEnum(ClearanceStatus), default=ClearanceStatus.PENDING, nullable=False
    )
    tax_paid:       Mapped[float|None]    = mapped_column(Numeric(12, 2), nullable=True)
    currency:       Mapped[str]           = mapped_column(String(3), default="USD")
    clearance_date: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    agent_name:     Mapped[str|None]      = mapped_column(String(255), nullable=True)
    agent_contact:  Mapped[str|None]      = mapped_column(String(255), nullable=True)
    notes:          Mapped[str|None]      = mapped_column(Text, nullable=True)
    extra_data:     Mapped[dict|None]     = mapped_column(JSONB, nullable=True)

    container: Mapped["Container"] = relationship("Container", back_populates="customs")

    def __repr__(self) -> str:
        return f"<CustomsClearance id={self.id} container_id={self.container_id} status={self.clearance_status}>"