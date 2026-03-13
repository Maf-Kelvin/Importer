# app/models/expense.py
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class ExpenseType(str, enum.Enum):
    LOADING_FEE = "loading_fee"
    SHIPPING_FEE = "shipping_fee"
    CLEARING_FEE = "clearing_fee"
    OFFLOADING_FEE = "offloading_fee"
    WAREHOUSE_FEE = "warehouse_fee"
    SECURITY_FEE = "security_fee"
    EXTRA_FEE = "extra_fee"


class ContainerExpense(BaseModel):
    __tablename__ = "container_expenses"
    
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=False)
    expense_type = Column(SQLEnum(ExpenseType), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    description = Column(String)
    
    # FX tracking
    fx_rate_to_usd = Column(Float, nullable=False, default=1.0)
    amount_usd = Column(Float, nullable=False)
    
    # Relationships
    container = relationship("Container", back_populates="expenses")
