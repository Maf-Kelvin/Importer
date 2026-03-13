# app/routers/tracking.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.routers.deps import get_db, get_current_active_user, get_clerk_or_higher_user
from app.models.user import User
from app.schemas.tracking import TrackingRecordInDB, NotificationSettingsUpdate
from app.services.tracking_service import TrackingService

router = APIRouter()


@router.post("/{container_id}/update")
def update_tracking(
    container_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Manually trigger tracking update for a container."""
    tracking_service = TrackingService(db)
    
    # Start background task
    background_tasks.add_task(
        tracking_service.update_container_tracking,
        container_id
    )
    
    return {"message": "Tracking update started"}


@router.get("/{container_id}/history", response_model=List[TrackingRecordInDB])
def get_tracking_history(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get tracking history for a container."""
    tracking_service = TrackingService(db)
    return tracking_service.get_tracking_history(container_id, current_user)


@router.get("/{container_id}/status")
def get_current_status(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get current tracking status for a container."""
    tracking_service = TrackingService(db)
    return tracking_service.get_current_status(container_id, current_user)


@router.post("/{container_id}/notifications")
def update_notification_settings(
    container_id: int,
    settings: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Update notification settings for container tracking."""
    tracking_service = TrackingService(db)
    result = tracking_service.update_notification_settings(container_id, settings, current_user)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    return {"message": "Notification settings updated"}