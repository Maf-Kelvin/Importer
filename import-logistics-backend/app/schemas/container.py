# app/schemas/container.py
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.container import ContainerType, AllocationMethod
from app.schemas.item import ItemInDB
from app.schemas.expense import ExpenseInDB


class ContainerBase(BaseModel):
    name: str
    container_type: ContainerType
    msc_container_number: Optional[str] = None
    allocation_method: AllocationMethod = AllocationMethod.WEIGHT_BASED
    notes: Optional[str] = None


class ContainerCreate(ContainerBase):
    pass


class ContainerUpdate(BaseModel):
    name: Optional[str] = None
    msc_container_number: Optional[str] = None
    allocation_method: Optional[AllocationMethod] = None
    notes: Optional[str] = None


class ContainerInDB(ContainerBase):
    id: int
    owner_id: int
    is_sealed: bool
    is_shipped: bool
    allocation_override: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ContainerWithItems(ContainerInDB):
    items: List[ItemInDB]
    expenses: List[ExpenseInDB]
    total_expenses: Optional[float] = None
    total_weight: Optional[float] = None
    total_value: Optional[float] = None
