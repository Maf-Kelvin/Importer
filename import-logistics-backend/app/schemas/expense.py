# app/schemas/expense.py
from typing import Optional
from pydantic import BaseModel, Field
from app.models.expense import ExpenseType


class ExpenseBase(BaseModel):
    container_id: int
    expense_type: ExpenseType
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    description: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    expense_type: Optional[ExpenseType] = None
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    description: Optional[str] = None


class ExpenseInDB(ExpenseBase):
    id: int
    fx_rate_to_usd: float
    amount_usd: float
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True