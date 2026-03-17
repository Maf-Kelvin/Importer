# app/models/__init__.py
# Import order matters — base first, then models with no FKs,
# then models that reference earlier ones.
# Alembic imports this file to discover all tables for autogenerate.

from app.models.base import Base, BaseModel, SoftDeleteModel  # noqa: F401

# Tenant foundation
from app.models.organization import Organization              # noqa: F401

# Users & auth
from app.models.user import User, UserRole                    # noqa: F401

# Core logistics
from app.models.container import Container, ContainerType, AllocationMethod  # noqa: F401
from app.models.expense import ContainerExpense, ExpenseType  # noqa: F401
from app.models.item import Item, ItemCondition, ItemCategory # noqa: F401
from app.models.pricing import PriceRecord, PricingMethod, PricingSource     # noqa: F401
from app.models.tracking import TrackingRecord, TrackingStatus               # noqa: F401

# Extended logistics
from app.models.logistics import (                            # noqa: F401
    Shipment, ShipmentStatus,
    Port,
    TransportLeg, TransportType,
    Document, DocumentType,
    CustomsClearance, ClearanceStatus,
)

# Warehouse
from app.models.warehouse import (                            # noqa: F401
    Warehouse,
    WarehouseInventory,
    InventoryMovement, MovementType,
)

# Commerce
from app.models.commerce import (                             # noqa: F401
    Customer,
    Supplier,
    Order, OrderStatus,
    OrderItem,
    Payment, PaymentMethod,
    Sale,
)

# Analytics & observability
from app.models.analytics import (                            # noqa: F401
    ExchangeRateHistory,
    Notification, NotificationType,
    AuditLog,
    DemandAnalytics,
)

__all__ = [
    "Base",
    "Organization",
    "User", "UserRole",
    "Container", "ContainerType", "AllocationMethod",
    "ContainerExpense", "ExpenseType",
    "Item", "ItemCondition", "ItemCategory",
    "PriceRecord", "PricingMethod", "PricingSource",
    "TrackingRecord", "TrackingStatus",
    "Shipment", "Port", "TransportLeg", "Document", "CustomsClearance",
    "Warehouse", "WarehouseInventory", "InventoryMovement",
    "Customer", "Supplier", "Order", "OrderItem", "Payment", "Sale",
    "ExchangeRateHistory", "Notification", "AuditLog", "DemandAnalytics",
]