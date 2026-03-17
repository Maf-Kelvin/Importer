# app/models/warehouse.py
import enum
from sqlalchemy import (
    Float, ForeignKey, Index, Integer,
    String, Text,  Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import BaseModel


class MovementType(str, enum.Enum):
    IN       = "in"
    OUT      = "out"
    TRANSFER = "transfer"
    ADJUST   = "adjust"


class Warehouse(BaseModel):
    __tablename__ = "warehouses"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    name:     Mapped[str]      = mapped_column(String(255), nullable=False)
    location: Mapped[str|None] = mapped_column(Text, nullable=True)
    capacity: Mapped[float|None] = mapped_column(Float, nullable=True)  # cubic meters
    manager:  Mapped[str|None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool]    = mapped_column(default=True, nullable=False)

    organization: Mapped["Organization"]             = relationship("Organization", back_populates="warehouses")
    inventory:    Mapped[list["WarehouseInventory"]] = relationship(
        "WarehouseInventory", back_populates="warehouse", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Warehouse id={self.id} name={self.name!r}>"


class WarehouseInventory(BaseModel):
    __tablename__ = "warehouse_inventory"

    warehouse_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    quantity:     Mapped[int]        = mapped_column(Integer, default=0, nullable=False)
    min_quantity: Mapped[int]        = mapped_column(Integer, default=0)  # reorder threshold
    shelf_location: Mapped[str|None] = mapped_column(String(100), nullable=True)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="inventory")
    item:      Mapped["Item"]      = relationship("Item",      back_populates="warehouse_inventory")
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement", back_populates="inventory_record", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_warehouseinv_warehouse_item", "warehouse_id", "item_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<WarehouseInventory warehouse={self.warehouse_id} item={self.item_id} qty={self.quantity}>"


class InventoryMovement(BaseModel):
    __tablename__ = "inventory_movements"

    inventory_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("warehouse_inventory.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    performed_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    movement_type: Mapped[MovementType] = mapped_column(SQLEnum(MovementType), nullable=False)
    quantity:      Mapped[int]          = mapped_column(Integer, nullable=False)
    reference:     Mapped[str|None]     = mapped_column(String(255), nullable=True)
    notes:         Mapped[str|None]     = mapped_column(Text, nullable=True)

    inventory_record: Mapped["WarehouseInventory"] = relationship(
        "WarehouseInventory", back_populates="movements"
    )

    def __repr__(self) -> str:
        return f"<InventoryMovement id={self.id} type={self.movement_type} qty={self.quantity}>"