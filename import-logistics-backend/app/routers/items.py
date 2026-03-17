# app/routers/items.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.routers.deps import ClerkUser, CurrentUser, DBDep
from app.schemas.common import PagedResponse, PaginationParams
from app.schemas.item import (
    ItemCreate,
    ItemInDB,
    ItemUpdate,
    ItemWithPricing,
    MarkSoldRequest,
)
from app.services.container_service import ContainerService

router = APIRouter()


@router.post(
    "/",
    response_model=ItemInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to a container",
)
async def create_item(
    data: ItemCreate,
    db: DBDep,
    current_user: ClerkUser,
):
    svc  = ContainerService(db)
    item = await svc.create_item(data, current_user)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container not found, sealed, or access denied",
        )
    return item


@router.get(
    "/",
    response_model=PagedResponse[ItemInDB],
    summary="List items with filters",
)
async def list_items(
    db: DBDep,
    current_user: CurrentUser,
    params:       PaginationParams = Depends(),
    container_id: Optional[int]    = Query(None),
    category:     Optional[str]    = Query(None),
    condition:    Optional[str]    = Query(None),
    sold:         Optional[bool]   = Query(None),
    search:       Optional[str]    = Query(None, description="Search by item name"),
):
    svc = ContainerService(db)
    return await svc.get_items(
        params=params,
        current_user=current_user,
        container_id=container_id,
        category=category,
        condition=condition,
        sold=sold,
        search=search,
    )


@router.get(
    "/{item_id}",
    response_model=ItemWithPricing,
    summary="Get item with full pricing history",
)
async def get_item(
    item_id: int,
    db: DBDep,
    current_user: CurrentUser,
):
    svc  = ContainerService(db)
    item = await svc.get_item_by_id(item_id, current_user)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.put(
    "/{item_id}",
    response_model=ItemInDB,
    summary="Update item details",
)
async def update_item(
    item_id: int,
    data: ItemUpdate,
    db: DBDep,
    current_user: ClerkUser,
):
    svc  = ContainerService(db)
    item = await svc.update_item(item_id, data, current_user)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.delete(
    "/{item_id}",
    summary="Soft-delete item",
)
async def delete_item(
    item_id: int,
    db: DBDep,
    current_user: ClerkUser,
):
    svc     = ContainerService(db)
    deleted = await svc.delete_item(item_id, current_user)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"message": "Item deleted"}


@router.post(
    "/{item_id}/mark-sold",
    response_model=ItemInDB,
    summary="Mark item as sold — creates a Sale record",
)
async def mark_item_sold(
    item_id: int,
    data: MarkSoldRequest,          # fixed: request body, not query params
    db: DBDep,
    current_user: ClerkUser,
):
    svc  = ContainerService(db)
    item = await svc.mark_item_sold(item_id, data, current_user)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item not found or already sold",
        )
    return item