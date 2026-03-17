# app/routers/containers.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.routers.deps import ClerkUser, CurrentUser, DBDep, ManagerUser
from app.schemas.common import PagedResponse, PaginationParams
from app.schemas.container import (
    ContainerCreate,
    ContainerInDB,
    ContainerUpdate,
    ContainerWithItems,
)
from app.services.container_service import ContainerService

router = APIRouter()


@router.post(
    "/",
    response_model=ContainerInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new container",
)
async def create_container(
    data: ContainerCreate,
    db: DBDep,
    current_user: ClerkUser,
):
    svc = ContainerService(db)
    return await svc.create_container(data, current_user)


@router.get(
    "/",
    response_model=PagedResponse[ContainerInDB],
    summary="List containers (role-filtered)",
)
async def list_containers(
    db: DBDep,
    current_user: CurrentUser,
    params: PaginationParams = Depends(),
    owner_id:       Optional[int]  = Query(None),
    container_type: Optional[str]  = Query(None),
    is_shipped:     Optional[bool] = Query(None),
):
    svc = ContainerService(db)
    return await svc.get_containers(
        params=params,
        current_user=current_user,
        owner_id=owner_id,
        container_type=container_type,
        is_shipped=is_shipped,
    )


@router.get(
    "/{container_id}",
    response_model=ContainerWithItems,
    summary="Get container with all items and expenses",
)
async def get_container(
    container_id: int,
    db: DBDep,
    current_user: CurrentUser,
):
    svc       = ContainerService(db)
    container = await svc.get_container_by_id(container_id, current_user)
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")
    return container


@router.put(
    "/{container_id}",
    response_model=ContainerInDB,
    summary="Update container",
)
async def update_container(
    container_id: int,
    data: ContainerUpdate,
    db: DBDep,
    current_user: ClerkUser,
):
    svc       = ContainerService(db)
    container = await svc.update_container(container_id, data, current_user)
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")
    return container


@router.delete(
    "/{container_id}",
    summary="Soft-delete container (manager+ only)",
)
async def delete_container(
    container_id: int,
    db: DBDep,
    current_user: ManagerUser,        # fixed: was undefined in original
):
    svc     = ContainerService(db)
    deleted = await svc.delete_container(container_id, current_user)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")
    return {"message": "Container deleted"}


@router.post(
    "/{container_id}/seal",
    summary="Seal container — no more items can be added",
)
async def seal_container(
    container_id: int,
    db: DBDep,
    current_user: ClerkUser,
):
    svc       = ContainerService(db)
    container = await svc.seal_container(container_id, current_user)
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")
    return {"message": "Container sealed", "container_id": container_id}


@router.post(
    "/{container_id}/allocate-costs",
    summary="Allocate container expenses to items",
)
async def allocate_costs(
    container_id: int,
    db: DBDep,
    current_user: ClerkUser,
    allocation_method: Optional[str] = Query(None, description="weight_based | value_based"),
):
    svc    = ContainerService(db)
    result = await svc.allocate_costs(container_id, allocation_method, current_user)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")
    return result