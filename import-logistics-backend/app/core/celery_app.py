# app/core/celery_app.py
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.core.config import settings

# ------------------------------------------------------------------------------
# App
# ------------------------------------------------------------------------------
celery_app = Celery(
    "import_logistics",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.fx_worker",
        "app.workers.tracking_worker",
        "app.workers.pricing_worker",
        "app.workers.notification_worker",
    ],
)

# ------------------------------------------------------------------------------
# Named queues — each worker type gets its own queue
# Prevents a flood of scraping jobs from starving tracking updates
# ------------------------------------------------------------------------------
_default_exchange = Exchange("default", type="direct")

QUEUES = (
    Queue("fx_queue",           _default_exchange, routing_key="fx_queue"),
    Queue("tracking_queue",     _default_exchange, routing_key="tracking_queue"),
    Queue("pricing_queue",      _default_exchange, routing_key="pricing_queue"),
    Queue("scraping_queue",     _default_exchange, routing_key="scraping_queue"),
    Queue("notification_queue", _default_exchange, routing_key="notification_queue"),
    Queue("default",            _default_exchange, routing_key="default"),
)

# ------------------------------------------------------------------------------
# Task routing — maps task module paths to queues
# ------------------------------------------------------------------------------
TASK_ROUTES = {
    "app.workers.fx_worker.*":           {"queue": "fx_queue"},
    "app.workers.tracking_worker.*":     {"queue": "tracking_queue"},
    "app.workers.pricing_worker.fetch_market_prices":  {"queue": "scraping_queue"},
    "app.workers.pricing_worker.update_item_pricing":  {"queue": "pricing_queue"},
    "app.workers.notification_worker.*": {"queue": "notification_queue"},
}

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Time
    timezone="UTC",
    enable_utc=True,

    # Reliability
    task_acks_late=True,            # task only acked after completion, not on pickup
    task_reject_on_worker_lost=True,# re-queue if worker dies mid-task
    task_track_started=True,
    worker_prefetch_multiplier=1,   # fair dispatch — prevents one worker hoarding tasks

    # Results
    result_expires=3600,

    # Queues
    task_queues=QUEUES,
    task_routes=TASK_ROUTES,
    task_default_queue="default",

    # Retry defaults (overridden per-task where needed)
    task_max_retries=3,
)

# ------------------------------------------------------------------------------
# Periodic beat schedule
# ------------------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    # FX rates — every hour
    "update-fx-rates": {
        "task":    "app.workers.fx_worker.update_fx_rates",
        "schedule": 3600.0,
        "options": {"queue": "fx_queue"},
    },
    # Tracking — every hour
    "update-all-tracking": {
        "task":    "app.workers.tracking_worker.update_all_tracking",
        "schedule": 3600.0,
        "options": {"queue": "tracking_queue"},
    },
    # Notifications — every hour
    "send-tracking-notifications": {
        "task":    "app.workers.notification_worker.send_tracking_notifications",
        "schedule": 3600.0,
        "options": {"queue": "notification_queue"},
    },
    # Demand analytics refresh — every 6 hours
    "refresh-demand-analytics": {
        "task":    "app.workers.pricing_worker.refresh_demand_analytics",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"queue": "pricing_queue"},
    },
}