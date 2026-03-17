# app/models/container.py
import enum
from sqlalchemy import (
    Boolean, ForeignKey, Index, Integer,
    String, Text, Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import SoftDeleteModel


class ContainerType(str, enum.Enum):
    TWENTY_FT = "20ft"
    FORTY_FT  = "40ft"


class AllocationMethod(str, enum.Enum):
    WEIGHT_BASED = "weight_based"
    VALUE_BASED  = "value_based"


class Container(SoftDeleteModel):
    __tablename__ = "containers"

    # Tenant
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    container_type: Mapped[ContainerType] = mapped_column(SQLEnum(ContainerType), nullable=False)
    msc_container_number: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)

    # Allocation
    allocation_method: Mapped[AllocationMethod] = mapped_column(
        SQLEnum(AllocationMethod), default=AllocationMethod.WEIGHT_BASED
    )
    allocation_override: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_sealed:   Mapped[bool] = mapped_column(Boolean, default=False)
    is_shipped:  Mapped[bool] = mapped_column(Boolean, default=False)

    # Ownership
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True,
    )

    # Metadata — renamed from `metadata` to avoid SQLAlchemy reserved attribute
    notes:      Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    organization: Mapped["Organization"]           = relationship("Organization", back_populates="containers")
    owner:        Mapped["User"]                   = relationship("User",         back_populates="containers")
    expenses:     Mapped[list["ContainerExpense"]] = relationship(
        "ContainerExpense", back_populates="container", cascade="all, delete-orphan"
    )
    items:        Mapped[list["Item"]] = relationship(
        "Item", back_populates="container", cascade="all, delete-orphan"
    )
    tracking_records: Mapped[list["TrackingRecord"]] = relationship(
        "TrackingRecord", back_populates="container", cascade="all, delete-orphan"
    )
    shipments:    Mapped[list["Shipment"]]         = relationship("Shipment", back_populates="container")
    documents:    Mapped[list["Document"]]         = relationship("Document", back_populates="container")
    customs:      Mapped[list["CustomsClearance"]] = relationship("CustomsClearance", back_populates="container")
    payments:     Mapped[list["Payment"]]          = relationship("Payment", back_populates="container")
    transport_legs: Mapped[list["TransportLeg"]]   = relationship("TransportLeg", back_populates="container")

    __table_args__ = (
        Index("ix_container_tenant_owner", "tenant_id", "owner_id"),
        Index("ix_container_tenant_shipped", "tenant_id", "is_shipped"),
    )

    def __repr__(self) -> str:
        return f"<Container id={self.id} name={self.name!r} type={self.container_type}>"