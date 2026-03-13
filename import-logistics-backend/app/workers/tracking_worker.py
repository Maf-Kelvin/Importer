# app/workers/tracking_worker.py
from celery import current_task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.tracking_service import TrackingService


@celery_app.task
def update_container_tracking(container_id: int):
    """Update tracking information for a specific container."""
    db = SessionLocal()
    try:
        tracking_service = TrackingService(db)
        return tracking_service.update_container_tracking(container_id)
    except Exception as exc:
        return {'status': 'FAILURE', 'error': str(exc)}
    finally:
        db.close()


@celery_app.task
def update_all_tracking():
    """Update tracking for all active containers."""
    db = SessionLocal()
    try:
        tracking_service = TrackingService(db)
        return tracking_service.update_all_tracking()
    except Exception as exc:
        return {'status': 'FAILURE', 'error': str(exc)}
    finally:
        db.close()