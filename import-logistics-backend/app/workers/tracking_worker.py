# app/workers/tracking_worker.py
import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.redis_lock import SyncRedisLock, LockNotAcquiredError

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    bind=True,
    name="app.workers.tracking_worker.update_container_tracking",
    max_retries=3,
    default_retry_delay=60,
    queue="tracking_queue",
)
def update_container_tracking(self, container_id: int):
    """Update tracking for a single container."""
    try:
        return _run(_do_update_container_tracking(container_id))
    except Exception as exc:
        logger.error(
            "Tracking update failed for container_id=%d: %s",
            container_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc)


async def _do_update_container_tracking(container_id: int) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.tracking_service import TrackingService

    async with AsyncSessionLocal() as db:
        svc = TrackingService(db)
        return await svc.update_container_tracking(container_id)


@celery_app.task(
    bind=True,
    name="app.workers.tracking_worker.update_all_tracking",
    max_retries=2,
    default_retry_delay=300,   # 5 min
    queue="tracking_queue",
)
def update_all_tracking(self):
    """
    Update tracking for all active shipped containers.
    Protected by distributed lock — only one worker runs at a time.
    Lock TTL = 50 min (just under the 1-hour schedule).
    """
    try:
        with SyncRedisLock("tracking_update", ttl_seconds=3000):
            return _run(_do_update_all_tracking())
    except LockNotAcquiredError:
        logger.info("Tracking update already running — skipping")
        return {"status": "skipped", "reason": "lock_held"}
    except Exception as exc:
        logger.error("update_all_tracking failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _do_update_all_tracking() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.tracking_service import TrackingService

    async with AsyncSessionLocal() as db:
        svc = TrackingService(db)
        result = await svc.update_all_tracking()

    logger.info(
        "Bulk tracking complete: updated=%d errors=%d total=%d",
        result.get("updated", 0),
        result.get("errors", 0),
        result.get("total", 0),
    )
    return result