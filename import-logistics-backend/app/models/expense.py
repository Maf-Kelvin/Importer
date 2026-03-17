# app/models/expense.py
import enum
from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.models.base import BaseModel


class ExpenseType(str, enum.Enum):
    LOADING_FEE    = "loading_fee"
    SHIPPING_FEE   = "shipping_fee"
    CLEARING_FEE   = "clearing_fee"
    OFFLOADING_FEE = "offloading_fee"
    WAREHOUSE_FEE  = "warehouse_fee"
    SECURITY_FEE   = "security_fee"
    EXTRA_FEE      = "extra_fee"


class ContainerExpense(BaseModel):
    __tablename__ = "container_expenses"

    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    container_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    expense_type: Mapped[ExpenseType] = mapped_column(SQLEnum(ExpenseType), nullable=False)
    amount:       Mapped[float]       = mapped_column(Float, nullable=False)
    currency:     Mapped[str]         = mapped_column(String(3), nullable=False, default="USD")
    description:  Mapped[str|None]    = mapped_column(Text, nullable=True)

    # FX tracking
    fx_rate_to_usd: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    amount_usd:     Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    container: Mapped["Container"] = relationship("Container", back_populates="expenses")

    __table_args__ = (
        Index("ix_expense_container_id", "container_id"),
        Index("ix_expense_tenant_id",    "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<ContainerExpense id={self.id} type={self.expense_type} amount_usd={self.amount_usd}>"