# app/schemas/container.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.container import AllocationMethod, ContainerType
from app.schemas.expense import ExpenseInDB
from app.schemas.item import ItemInDB


# ------------------------------------------------------------------------------
# Container
# ------------------------------------------------------------------------------
class ContainerBase(BaseModel):
    name:                 str
    container_type:       ContainerType
    msc_container_number: Optional[str]      = None
    allocation_method:    AllocationMethod   = AllocationMethod.WEIGHT_BASED
    notes:                Optional[str]      = None


class ContainerCreate(ContainerBase):
    pass


class ContainerUpdate(BaseModel):
    name:                 Optional[str]              = None
    msc_container_number: Optional[str]              = None
    allocation_method:    Optional[AllocationMethod] = None
    notes:                Optional[str]              = None


class ContainerInDB(ContainerBase):
    id:                  int
    tenant_id:           int
    owner_id:            int
    is_sealed:           bool
    is_shipped:          bool
    allocation_override: bool
    created_at:          datetime          # fixed: was str
    updated_at:          datetime          # fixed: was str
    deleted_at:          Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ContainerWithItems(ContainerInDB):
    items:          List[ItemInDB]    = []
    expenses:       List[ExpenseInDB] = []
    # Computed summary fields — populated by service layer
    total_expenses: Optional[float]  = None
    total_weight:   Optional[float]  = None
    total_value:    Optional[float]  = None
    item_count:     int              = 0
    items_sold:     int              = 0