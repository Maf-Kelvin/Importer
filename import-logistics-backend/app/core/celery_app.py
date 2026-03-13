# app/core/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "import_logistics",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.pricing_worker",
        "app.workers.tracking_worker", 
        "app.workers.fx_worker",
        "app.workers.notification_worker"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_serializer_type="json",
    result_expires=3600,  # 1 hour
)

# Periodic tasks configuration
celery_app.conf.beat_schedule = {
    "update-fx-rates": {
        "task": "app.workers.fx_worker.update_fx_rates",
        "schedule": 3600.0,  # Every hour
    },
    "update-tracking-status": {
        "task": "app.workers.tracking_worker.update_all_tracking",
        "schedule": 3600.0,  # Every hour
    },
    "send-tracking-notifications": {
        "task": "app.workers.notification_worker.send_tracking_notifications", 
        "schedule": 3600.0,  # Every hour
    },
}
