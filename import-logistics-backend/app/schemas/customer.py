# app/schemas/customer.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    name:    str                = Field(..., min_length=1, max_length=255)
    email:   Optional[EmailStr] = None
    phone:   Optional[str]      = Field(None, max_length=50)
    address: Optional[str]      = None
    notes:   Optional[str]      = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name:    Optional[str]      = Field(None, min_length=1, max_length=255)
    email:   Optional[EmailStr] = None
    phone:   Optional[str]      = Field(None, max_length=50)
    address: Optional[str]      = None
    notes:   Optional[str]      = None


class CustomerInDB(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id:         int
    created_at: datetime
    updated_at: datetime
