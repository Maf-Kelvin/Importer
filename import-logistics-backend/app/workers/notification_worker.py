# app/workers/notification_worker.py
from datetime import datetime, timedelta
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.notification_service import NotificationService
from app.models.container import Container
from app.models.tracking import TrackingRecord


@celery_app.task
def send_tracking_notifications():
    """Send tracking notifications for containers."""
    db = SessionLocal()
    try:
        notification_service = NotificationService()
        
        # Find containers that need notifications
        containers_needing_notifications = db.query(Container).join(
            TrackingRecord
        ).filter(
            Container.is_shipped == True,
            TrackingRecord.notification_sent == False
        ).all()
        
        sent_count = 0
        for container in containers_needing_notifications:
            try:
                notification_service.send_tracking_notification(container.id)
                sent_count += 1
            except Exception as e:
                print(f"Error sending notification for container {container.id}: {e}")
        
        return {
            'status': 'SUCCESS',
            'notifications_sent': sent_count
        }
        
    except Exception as exc:
        return {'status': 'FAILURE', 'error': str(exc)}
    finally:
        db.close()


@celery_app.task
def send_custom_notification(container_id: int, message: str, recipients: list):
    """Send custom notification for a container."""
    notification_service = NotificationService()
    try:
        return notification_service.send_custom_notification(container_id, message, recipients)
    except Exception as exc:
        return {'status': 'FAILURE', 'error': str(exc)}