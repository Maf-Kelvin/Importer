# app/routers/items.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.routers.deps import get_db, get_current_active_user, get_clerk_or_higher_user
from app.models.user import User
from app.schemas.item import ItemCreate, ItemUpdate, ItemInDB, ItemWithPricing
from app.schemas.common import PaginatedResponse
from app.services.container_service import ContainerService

router = APIRouter()


@router.post("/", response_model=ItemInDB)
def create_item(
    item_create: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Create new item in container."""
    container_service = ContainerService(db)
    return container_service.create_item(item_create, current_user)


@router.get("/", response_model=PaginatedResponse[ItemInDB])
def get_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    container_id: Optional[int] = None,
    category: Optional[str] = None,
    condition: Optional[str] = None,
    sold: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get items with filtering."""
    container_service = ContainerService(db)
    return container_service.get_items(
        skip=skip,
        limit=limit,
        container_id=container_id,
        category=category,
        condition=condition,
        sold=sold,
        current_user=current_user
    )


@router.get("/{item_id}", response_model=ItemWithPricing)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get item by ID with pricing info."""
    container_service = ContainerService(db)
    item = container_service.get_item_by_id(item_id, current_user)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return item


@router.put("/{item_id}", response_model=ItemInDB)
def update_item(
    item_id: int,
    item_update: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Update item."""
    container_service = ContainerService(db)
    item = container_service.update_item(item_id, item_update, current_user)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return item


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Delete item."""
    container_service = ContainerService(db)
    success = container_service.delete_item(item_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {"message": "Item deleted successfully"}


@router.post("/{item_id}/mark-sold")
def mark_item_sold(
    item_id: int,
    selling_price: float,
    sold_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Mark item as sold."""
    container_service = ContainerService(db)
    item = container_service.mark_item_sold(item_id, selling_price, sold_date, current_user)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {"message": "Item marked as sold", "item": item}
