# app/workers/maintenance_worker.py
import asyncio
import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    name="app.workers.maintenance_worker.purge_expired_idempotency_keys",
    queue="default",
)
def purge_expired_idempotency_keys() -> dict:
    """Delete idempotency records whose replay window (or stuck claim) has expired."""
    return _run(_purge())


async def _purge() -> dict:
    from sqlalchemy import delete

    from app.core.database import AsyncSessionLocal
    from app.models.idempotency import IdempotencyKey

    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                delete(IdempotencyKey).where(IdempotencyKey.expires_at < datetime.now(timezone.utc))
            )
    logger.info("Purged %d expired idempotency keys", result.rowcount)
    return {"deleted": result.rowcount}
