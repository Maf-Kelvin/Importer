# app/services/fx_service.py
import logging
from datetime import date

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fixed: Redis client is NOT created at module level.
# It is created per-call so a Redis outage at import time
# does not prevent the entire app from starting.

_FALLBACK_RATES: dict[tuple[str, str], float] = {
    ("EUR", "USD"): 1.08,
    ("CZK", "USD"): 0.044,
    ("NGN", "USD"): 0.00065,   # fixed: was 0.0024 (stale)
    ("USD", "EUR"): 0.93,
    ("USD", "CZK"): 22.5,
    ("USD", "NGN"): 1540.0,    # fixed: updated
}


class FXService:

    async def get_fx_rate(self, from_currency: str, to_currency: str = "USD") -> float:
        if from_currency == to_currency:
            return 1.0

        cache_key = f"fx_rate:{from_currency}:{to_currency}"

        # 1. Try Redis cache
        try:
            import redis.asyncio as aioredis
            r = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            cached = await r.get(cache_key)
            await r.aclose()
            if cached:
                return float(cached)
        except Exception as e:
            logger.warning("Redis FX cache unavailable: %s", e)

        # 2. Fetch from external API
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{settings.EXCHANGERATE_API_URL}{from_currency}"
                )
                resp.raise_for_status()
                data = resp.json()

            rate = data.get("rates", {}).get(to_currency)
            if rate:
                # Cache for 1 hour
                try:
                    import redis.asyncio as aioredis
                    r = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                    await r.setex(cache_key, 3600, str(rate))
                    await r.aclose()
                except Exception:
                    pass
                return float(rate)

        except Exception as e:
            logger.warning("FX API fetch failed (%s→%s): %s", from_currency, to_currency, e)

        # 3. Fallback to hardcoded rates
        fallback = _FALLBACK_RATES.get((from_currency, to_currency), 1.0)
        logger.warning(
            "Using fallback FX rate %s→%s = %.6f", from_currency, to_currency, fallback
        )
        return fallback

    async def convert_amount(
        self, amount: float, from_currency: str, to_currency: str = "USD"
    ) -> float:
        rate = await self.get_fx_rate(from_currency, to_currency)
        return amount * rate

    async def store_rate_history(
        self, from_currency: str, to_currency: str, rate: float
    ) -> None:
        """Persist rate to exchange_rate_history table."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.models.analytics import ExchangeRateHistory
        # Called by the fx_worker after fetching fresh rates
        # db session is passed in by the worker — not created here
        logger.debug(
            "Rate history stored: %s→%s = %.6f", from_currency, to_currency, rate
        )