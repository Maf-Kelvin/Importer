# app/workers/notification_worker.py
import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    bind=True,
    name="app.workers.notification_worker.send_tracking_notifications",
    max_retries=3,
    default_retry_delay=120,
    queue="notification_queue",
)
def send_tracking_notifications(self):
    """
    Find all shipped containers with unsent notifications
    and dispatch email alerts to their owners.
    """
    try:
        return _run(_do_send_tracking_notifications())
    except Exception as exc:
        logger.error("send_tracking_notifications failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _do_send_tracking_notifications() -> dict:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, transaction
    from app.models.container import Container
    from app.models.tracking import TrackingRecord
    from app.services.notification_service import NotificationService

    svc = NotificationService()
    sent = 0
    errors = 0

    async with AsyncSessionLocal() as db:
        # Find tracking records that haven't been notified yet
        result = await db.execute(
            select(TrackingRecord)
            .join(Container)
            .where(
                Container.is_shipped == True,        # noqa: E712
                TrackingRecord.notification_sent == False,  # noqa: E712
            )
            .limit(100)   # process in batches to avoid timeout
        )
        records = result.scalars().all()

        for record in records:
            try:
                res = await svc.send_tracking_notification(record.container_id)
                if res.get("status") == "success":
                    async with transaction(db):
                        record.notification_sent = True
                    sent += 1
                else:
                    logger.warning(
                        "Notification skipped container_id=%d: %s",
                        record.container_id, res.get("reason"),
                    )
                    errors += 1
            except Exception as e:
                logger.error(
                    "Notification failed container_id=%d: %s",
                    record.container_id, e, exc_info=True,
                )
                errors += 1

    logger.info("Tracking notifications: sent=%d errors=%d", sent, errors)
    return {"status": "success", "sent": sent, "errors": errors}


@celery_app.task(
    bind=True,
    name="app.workers.notification_worker.send_custom_notification",
    max_retries=3,
    default_retry_delay=60,
    queue="notification_queue",
)
def send_custom_notification(
    self, container_id: int, message: str, recipients: list[str]
):
    """Send a custom notification message to a list of recipients."""
    try:
        return _run(_do_send_custom_notification(container_id, message, recipients))
    except Exception as exc:
        logger.error(
            "send_custom_notification failed container_id=%d: %s",
            container_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc)


async def _do_send_custom_notification(
    container_id: int, message: str, recipients: list[str]
) -> dict:
    from app.services.notification_service import NotificationService

    svc = NotificationService()
    result = await svc.send_custom_notification(container_id, message, recipients)
    logger.info(
        "Custom notification dispatched: container_id=%d recipients=%d",
        container_id, len(recipients),
    )
    return result


@celery_app.task(
    bind=True,
    name="app.workers.notification_worker.notify_low_stock",
    max_retries=2,
    default_retry_delay=300,
    queue="notification_queue",
)
def notify_low_stock(self):
    """
    Check warehouse inventory levels and notify managers
    when items fall below their minimum threshold.
    """
    try:
        return _run(_do_notify_low_stock())
    except Exception as exc:
        logger.error("notify_low_stock failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _do_notify_low_stock() -> dict:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.warehouse import WarehouseInventory
    from app.models.item import Item
    from app.models.user import User, UserRole
    from app.services.notification_service import NotificationService, EmailMessage

    alerts = 0
    svc    = NotificationService()

    async with AsyncSessionLocal() as db:
        # Find inventory records below minimum quantity
        result = await db.execute(
            select(WarehouseInventory)
            .where(WarehouseInventory.quantity <= WarehouseInventory.min_quantity)
            .where(WarehouseInventory.min_quantity > 0)
        )
        low_records = result.scalars().all()

        if not low_records:
            return {"status": "success", "alerts": 0}

        for inv in low_records:
            item_result = await db.execute(
                select(Item).where(Item.id == inv.item_id)
            )
            item = item_result.scalar_one_or_none()
            if not item:
                continue

            # Notify tenant managers
            managers_result = await db.execute(
                select(User).where(
                    User.tenant_id == item.tenant_id,
                    User.role.in_([UserRole.ADMIN, UserRole.MANAGER]),
                    User.is_active == True,  # noqa: E712
                )
            )
            managers = managers_result.scalars().all()

            for manager in managers:
                msg = EmailMessage(
                    to_email=manager.email,
                    subject=f"Low Stock Alert — {item.name}",
                    body=(
                        f"Dear {manager.first_name},\n\n"
                        f"Item '{item.name}' is below minimum stock level.\n"
                        f"Current quantity: {inv.quantity}\n"
                        f"Minimum threshold: {inv.min_quantity}\n\n"
                        f"Please arrange a reorder.\n\n"
                        f"— Import Logistics System"
                    ),
                )
                await svc._provider.send(msg)
                alerts += 1

    logger.info("Low stock alerts sent: %d", alerts)
    return {"status": "success", "alerts": alerts}