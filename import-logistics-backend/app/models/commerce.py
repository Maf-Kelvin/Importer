# app/models/commerce.py
import enum
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index,
    Integer, Numeric, String, Text, Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import SoftDeleteModel, BaseModel


# ==============================================================================
# Customers
# ==============================================================================
class Customer(SoftDeleteModel):
    __tablename__ = "customers"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    name:    Mapped[str]      = mapped_column(String(255), nullable=False)
    email:   Mapped[str|None] = mapped_column(String(255), nullable=True, index=True)
    phone:   Mapped[str|None] = mapped_column(String(50),  nullable=True)
    address: Mapped[str|None] = mapped_column(Text, nullable=True)
    notes:   Mapped[str|None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"]  = relationship("Organization", back_populates="customers")
    orders:       Mapped[list["Order"]]   = relationship("Order", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.name!r}>"


# ==============================================================================
# Suppliers
# ==============================================================================
class Supplier(SoftDeleteModel):
    __tablename__ = "suppliers"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    supplier_name: Mapped[str]      = mapped_column(String(255), nullable=False)
    country:       Mapped[str|None] = mapped_column(String(100), nullable=True)
    contact_info:  Mapped[str|None] = mapped_column(Text, nullable=True)
    email:         Mapped[str|None] = mapped_column(String(255), nullable=True)
    phone:         Mapped[str|None] = mapped_column(String(50),  nullable=True)
    rating:        Mapped[float|None] = mapped_column(Float, nullable=True)  # 0-5 stars
    is_active:     Mapped[bool]     = mapped_column(Boolean, default=True)
    extra_data:    Mapped[dict|None] = mapped_column(JSONB, nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="suppliers")

    def __repr__(self) -> str:
        return f"<Supplier id={self.id} name={self.supplier_name!r}>"


# ==============================================================================
# Orders
# ==============================================================================
class OrderStatus(str, enum.Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    FULFILLED = "fulfilled"
    CANCELED  = "canceled"


class Order(BaseModel):
    __tablename__ = "orders"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    status:   Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    total:    Mapped[float|None]  = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str]         = mapped_column(String(3), default="USD")
    notes:    Mapped[str|None]    = mapped_column(Text, nullable=True)

    customer:    Mapped["Customer"]        = relationship("Customer",   back_populates="orders")
    created_by:  Mapped["User"]            = relationship("User",       back_populates="orders")
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="order")

    __table_args__ = (
        Index("ix_order_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_order_tenant_status",   "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} status={self.status} total={self.total}>"


class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )

    quantity: Mapped[int]         = mapped_column(Integer, nullable=False)
    price:    Mapped[float]       = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str]         = mapped_column(String(3), default="USD")

    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    item:  Mapped["Item"]  = relationship("Item")

    def __repr__(self) -> str:
        return f"<OrderItem id={self.id} order={self.order_id} item={self.item_id} qty={self.quantity}>"


# ==============================================================================
# Payments
# ==============================================================================
class PaymentMethod(str, enum.Enum):
    CASH         = "cash"
    BANK_TRANSFER = "bank_transfer"
    CARD         = "card"
    STRIPE       = "stripe"
    OTHER        = "other"


class Payment(BaseModel):
    __tablename__ = "payments"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    container_id: Mapped[int|None] = mapped_column(
        Integer, ForeignKey("containers.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    order_id: Mapped[int|None] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    amount:         Mapped[float]               = mapped_column(Numeric(14, 2), nullable=False)
    currency:       Mapped[str]                 = mapped_column(String(3), default="USD")
    payment_method: Mapped[PaymentMethod]       = mapped_column(SQLEnum(PaymentMethod), nullable=False)
    paid_at:        Mapped[datetime|None]       = mapped_column(DateTime(timezone=True), nullable=True)
    reference:      Mapped[str|None]            = mapped_column(String(255), nullable=True)
    notes:          Mapped[str|None]            = mapped_column(Text, nullable=True)

    container: Mapped["Container|None"] = relationship("Container", back_populates="payments")
    order:     Mapped["Order|None"]     = relationship("Order",     back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} amount={self.amount} method={self.payment_method}>"


# ==============================================================================
# Sales (dedicated record when an item is sold — replaces sold boolean on Item)
# ==============================================================================
class Sale(BaseModel):
    __tablename__ = "sales"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False, unique=True, index=True,  # one sale per item
    )
    customer_id: Mapped[int|None] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    sold_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    sale_price: Mapped[float]         = mapped_column(Numeric(14, 2), nullable=False)
    currency:   Mapped[str]           = mapped_column(String(3), default="USD")
    sold_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    notes:      Mapped[str|None]      = mapped_column(Text, nullable=True)

    item:     Mapped["Item"]          = relationship("Item",     back_populates="sale")
    customer: Mapped["Customer|None"] = relationship("Customer")

    __table_args__ = (
        Index("ix_sale_tenant_sold_at", "tenant_id", "sold_at"),
    )

    def __repr__(self) -> str:
        return f"<Sale id={self.id} item_id={self.item_id} price={self.sale_price}>"