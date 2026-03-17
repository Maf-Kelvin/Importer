# app/schemas/common.py
from __future__ import annotations

import math
from typing import Generic, List, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, field_validator

T = TypeVar("T")


# ------------------------------------------------------------------------------
# Pagination params — shared FastAPI dependency
# Usage in router:
#   async def list_items(p: PaginationParams = Depends()):
# ------------------------------------------------------------------------------
class PaginationParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page:  int = Query(default=1,  ge=1,             description="Page number (1-based)")
    limit: int = Query(default=20, ge=1, le=100,     description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


# ------------------------------------------------------------------------------
# Cursor-based pagination params — for large datasets
# Usage in router:
#   async def list_items(p: CursorPaginationParams = Depends()):
# ------------------------------------------------------------------------------
class CursorPaginationParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cursor: Optional[str] = Query(default=None, description="Opaque cursor from previous page")
    limit:  int           = Query(default=20, ge=1, le=100)


# ------------------------------------------------------------------------------
# Standard paginated response — works with both offset and cursor pagination
# ------------------------------------------------------------------------------
class PagedResponse(BaseModel, Generic[T]):
    """
    Standard envelope for all list endpoints.

    {
        "items":    [...],
        "total":    142,
        "page":     2,
        "limit":    20,
        "pages":    8,
        "has_next": true,
        "has_prev": true
    }
    """
    items:    List[T]
    total:    int
    page:     int
    limit:    int
    pages:    int
    has_next: bool
    has_prev: bool

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def create(cls, items: List[T], total: int, params: PaginationParams) -> "PagedResponse[T]":
        pages = math.ceil(total / params.limit) if params.limit else 1
        return cls(
            items=items,
            total=total,
            page=params.page,
            limit=params.limit,
            pages=pages,
            has_next=params.page < pages,
            has_prev=params.page > 1,
        )


# ------------------------------------------------------------------------------
# Cursor response envelope
# ------------------------------------------------------------------------------
class CursorPagedResponse(BaseModel, Generic[T]):
    items:       List[T]
    next_cursor: Optional[str] = None
    has_next:    bool

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ------------------------------------------------------------------------------
# Generic message / error responses
# ------------------------------------------------------------------------------
class ResponseMessage(BaseModel):
    message: str


class ErrorDetail(BaseModel):
    code:    str
    message: str
    field:   Optional[str] = None


class ErrorResponse(BaseModel):
    error:   str
    details: Optional[List[ErrorDetail]] = None