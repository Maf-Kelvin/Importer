# app/workers/fx_worker.py
import asyncio
import logging
from datetime import date

from app.core.celery_app import celery_app
from app.core.config import SUPPORTED_CURRENCIES
from app.core.redis_lock import SyncRedisLock, LockNotAcquiredError

logger = logging.getLogger(__name__)


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    bind=True,
    name="app.workers.fx_worker.update_fx_rates",
    max_retries=3,
    default_retry_delay=120,   # 2 min between retries
    queue="fx_queue",
)
def update_fx_rates(self):
    """
    Fetch fresh FX rates for all supported currencies and persist
    to exchange_rate_history. Protected by a distributed lock so
    only one worker runs this at a time.
    Lock TTL = 55 min (just under the 1-hour schedule interval).
    """
    try:
        with SyncRedisLock("fx_update", ttl_seconds=3300):
            return _run(_do_update_fx_rates())
    except LockNotAcquiredError:
        logger.info("FX update already running — skipping this invocation")
        return {"status": "skipped", "reason": "lock_held"}
    except Exception as exc:
        logger.error("FX update failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _do_update_fx_rates() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.models.analytics import ExchangeRateHistory
    from app.services.fx_service import FXService
    from app.core.database import transaction

    fx   = FXService()
    today = date.today()
    results: dict[str, float | str] = {}

    async with AsyncSessionLocal() as db:
        for currency in SUPPORTED_CURRENCIES:
            if currency == "USD":
                continue
            try:
                rate = await fx.get_fx_rate(currency, "USD")
                results[f"{currency}_USD"] = rate

                # Persist to history table (upsert pattern)
                async with transaction(db):
                    from sqlalchemy import select
                    existing = await db.execute(
                        select(ExchangeRateHistory).where(
                            ExchangeRateHistory.from_currency == currency,
                            ExchangeRateHistory.to_currency   == "USD",
                            ExchangeRateHistory.date          == today,
                        )
                    )
                    record = existing.scalar_one_or_none()
                    if record:
                        record.rate = rate
                    else:
                        db.add(ExchangeRateHistory(
                            from_currency=currency,
                            to_currency="USD",
                            rate=rate,
                            date=today,
                            source="exchangerate-api",
                        ))

            except Exception as e:
                logger.error("Failed to fetch FX rate for %s: %s", currency, e)
                results[f"{currency}_USD"] = f"error: {e}"

    success_count = sum(1 for v in results.values() if isinstance(v, float))
    logger.info("FX rates updated: %d/%d", success_count, len(results))
    return {
        "status":        "success",
        "rates_updated": success_count,
        "rates":         results,
    }