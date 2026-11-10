# app/services/fx_service.py
import logging
from decimal import Decimal, InvalidOperation

import httpx

from app.core.config import settings
from app.core.redis_clients import get_cache_redis
from app.utils.money import convert, to_decimal

logger = logging.getLogger(__name__)

# Development / emergency fallback only. These are NOT used in production
# unless FX_ALLOW_FALLBACK=true, because silently using a stale hard-coded
# rate for a financial calculation is worse than failing loudly.
_FALLBACK_RATES: dict[tuple[str, str], Decimal] = {
    ("EUR", "USD"): Decimal("1.08"),
    ("CZK", "USD"): Decimal("0.044"),
    ("NGN", "USD"): Decimal("0.00065"),
    ("USD", "EUR"): Decimal("0.93"),
    ("USD", "CZK"): Decimal("22.5"),
    ("USD", "NGN"): Decimal("1540"),
}


class FXRateUnavailable(Exception):
    """No trustworthy exchange rate could be obtained."""


def _fallback_allowed() -> bool:
    return settings.ENVIRONMENT != "production" or settings.FX_ALLOW_FALLBACK


class FXService:

    async def get_fx_rate(self, from_currency: str, to_currency: str = "USD") -> Decimal:
        from_currency, to_currency = from_currency.upper(), to_currency.upper()
        if from_currency == to_currency:
            return Decimal("1")

        cache_key = f"fx_rate:{from_currency}:{to_currency}"

        # 1. Cache (disposable Redis)
        try:
            cached = await get_cache_redis().get(cache_key)
            if cached:
                return to_decimal(cached)
        except Exception as exc:
            logger.warning("FX cache unavailable: %s", exc)

        # 2. Live provider
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{settings.EXCHANGERATE_API_URL}{from_currency}")
                resp.raise_for_status()
                data = resp.json()
            raw = data.get("rates", {}).get(to_currency)
            if raw is not None:
                rate = to_decimal(raw)
                if rate > 0:
                    try:
                        await get_cache_redis().setex(cache_key, 3600, str(rate))
                    except Exception as exc:
                        logger.warning("Could not cache FX rate: %s", exc)
                    return rate
        except (httpx.HTTPError, ValueError, InvalidOperation) as exc:
            logger.warning("FX fetch failed (%s->%s): %s", from_currency, to_currency, exc)

        # 3. Fallback - explicit, logged, and never silent in production
        fallback = _FALLBACK_RATES.get((from_currency, to_currency))
        if fallback is not None and _fallback_allowed():
            logger.warning(
                "USING FALLBACK FX RATE %s->%s = %s", from_currency, to_currency, fallback
            )
            return fallback

        raise FXRateUnavailable(
            f"No exchange rate available for {from_currency}->{to_currency}"
        )

    async def convert_amount(
        self, amount: Decimal, from_currency: str, to_currency: str = "USD"
    ) -> Decimal:
        rate = await self.get_fx_rate(from_currency, to_currency)
        return convert(amount, rate)

    async def store_rate_history(
        self, from_currency: str, to_currency: str, rate: Decimal
    ) -> None:
        """Placeholder hook: persistence is done by fx_worker, not here."""
        logger.debug("FX rate observed: %s->%s = %s", from_currency, to_currency, rate)
