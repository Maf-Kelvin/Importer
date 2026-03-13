# app/routers/containers.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.routers.deps import get_db, get_current_active_user, get_clerk_or_higher_user
from app.models.user import User
from app.schemas.container import ContainerCreate, ContainerUpdate, ContainerInDB, ContainerWithItems
from app.schemas.common import PaginatedResponse
from app.services.container_service import ContainerService

router = APIRouter()


@router.post("/", response_model=ContainerInDB)
def create_container(
    container_create: ContainerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Create new container."""
    container_service = ContainerService(db)
    return container_service.create_container(container_create, current_user.id)


@router.get("/", response_model=PaginatedResponse[ContainerInDB])
def get_containers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    owner_id: Optional[int] = None,
    container_type: Optional[str] = None,
    is_shipped: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get containers with optional filtering."""
    container_service = ContainerService(db)
    return container_service.get_containers(
        skip=skip,
        limit=limit,
        owner_id=owner_id,
        container_type=container_type,
        is_shipped=is_shipped,
        current_user=current_user
    )


@router.get("/{container_id}", response_model=ContainerWithItems)
def get_container(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get container by ID with items."""
    container_service = ContainerService(db)
    container = container_service.get_container_by_id(container_id, current_user)
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    return container


@router.put("/{container_id}", response_model=ContainerInDB)
def update_container(
    container_id: int,
    container_update: ContainerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Update container."""
    container_service = ContainerService(db)
    container = container_service.update_container(container_id, container_update, current_user)
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    return container


@router.delete("/{container_id}")
def delete_container(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_manager_or_admin_user)
) -> Any:
    """Delete container (requires manager+ role)."""
    container_service = ContainerService(db)
    success = container_service.delete_container(container_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    return {"message": "Container deleted successfully"}


@router.post("/{container_id}/seal")
def seal_container(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Seal container (no more items can be added)."""
    container_service = ContainerService(db)
    container = container_service.seal_container(container_id, current_user)
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    return {"message": "Container sealed successfully"}


@router.post("/{container_id}/allocate-costs")
def allocate_costs(
    container_id: int,
    allocation_method: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Allocate container costs to items."""
    container_service = ContainerService(db)
    result = container_service.allocate_costs(container_id, allocation_method, current_user)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    return result