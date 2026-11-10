# app/routers/tracking.py
from fastapi import APIRouter, HTTPException, status

from app.routers.deps import ClerkUser, CurrentUser, DBDep
from app.schemas.tracking import (
    NotificationSettingsUpdate,
    TrackingRecordInDB,
    TrackingStatusResponse,
)
from app.services.tracking_service import TrackingService

router = APIRouter()


@router.post(
    "/{container_id}/update",
    summary="Manually trigger a tracking update (async)",
)
async def trigger_tracking_update(
    container_id: int,
    db: DBDep,
    current_user: ClerkUser,
):
    # The caller must be allowed to see this container (same tenant; clerks: own only).
    # Previously ANY user could queue an update for ANY tenant's container.
    svc = TrackingService(db)
    if not await svc._get_container_with_permission(container_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")

    from app.workers.tracking_worker import update_container_tracking
    # queue is an apply_async option, NOT a task keyword argument
    update_container_tracking.apply_async(
        args=[container_id, current_user.tenant_id], queue="tracking_queue"
    )
    return {"message": "Tracking update queued", "container_id": container_id}


@router.get(
    "/{container_id}/history",
    response_model=list[TrackingRecordInDB],
    summary="Get full tracking history for a container",
)
async def get_tracking_history(
    container_id: int, db: DBDep, current_user: CurrentUser
):
    svc = TrackingService(db)
    return await svc.get_tracking_history(container_id, current_user)


@router.get(
    "/{container_id}/status",
    response_model=TrackingStatusResponse,
    summary="Get current tracking status",
)
async def get_current_status(
    container_id: int, db: DBDep, current_user: CurrentUser
):
    svc    = TrackingService(db)
    result = await svc.get_current_status(container_id, current_user)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tracking data found for this container",
        )
    return result


@router.post(
    "/{container_id}/notifications",
    summary="Update tracking notification settings for a container",
)
async def update_notification_settings(
    container_id: int,
    data: NotificationSettingsUpdate,
    db: DBDep,
    current_user: ClerkUser,
):
    svc    = TrackingService(db)
    result = await svc.update_notification_settings(  # fixed: method now exists
        container_id, data, current_user
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")
    return result