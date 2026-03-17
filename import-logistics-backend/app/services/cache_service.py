# app/services/cache_service.py
import json
import logging
from typing import Any, Optional, Type, TypeVar

import redis.asyncio as aioredis
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ------------------------------------------------------------------------------
# TTL constants (seconds)
# ------------------------------------------------------------------------------
TTL_DASHBOARD   = 300     # 5 minutes
TTL_FX_RATE     = 3600    # 1 hour
TTL_PRICING     = 1800    # 30 minutes
TTL_SHORT       = 60      # 1 minute
TTL_LONG        = 86400   # 24 hours


class CacheService:
    """
    Redis-backed cache with Pydantic model serialisation.

    Usage:
        cache = CacheService()

        # Store
        await cache.set("dashboard:1", summary_obj, ttl=300)

        # Retrieve as Pydantic model
        summary = await cache.get("dashboard:1", DashboardSummary)

        # Retrieve raw dict
        data = await cache.get_raw("fx_rate:EUR:USD")

        # Invalidate by pattern
        await cache.invalidate_pattern("dashboard:*")
    """

    async def _client(self) -> aioredis.Redis:
        return await aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------
    async def get(self, key: str, model: Type[T]) -> Optional[T]:
        """Retrieve a Pydantic model from cache."""
        try:
            r      = await self._client()
            raw    = await r.get(key)
            await r.aclose()
            if raw:
                return model.model_validate_json(raw)
        except Exception as e:
            logger.warning("Cache GET failed key=%s: %s", key, e)
        return None

    async def get_raw(self, key: str) -> Optional[Any]:
        """Retrieve raw JSON-decoded value from cache."""
        try:
            r   = await self._client()
            raw = await r.get(key)
            await r.aclose()
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning("Cache GET_RAW failed key=%s: %s", key, e)
        return None

    # ------------------------------------------------------------------
    # Set
    # ------------------------------------------------------------------
    async def set(self, key: str, value: BaseModel | Any, ttl: int = TTL_SHORT) -> bool:
        """Store a value. Pydantic models are serialised automatically."""
        try:
            r = await self._client()
            if isinstance(value, BaseModel):
                payload = value.model_dump_json()
            else:
                payload = json.dumps(value)
            await r.setex(key, ttl, payload)
            await r.aclose()
            return True
        except Exception as e:
            logger.warning("Cache SET failed key=%s: %s", key, e)
            return False

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    async def delete(self, key: str) -> bool:
        try:
            r = await self._client()
            await r.delete(key)
            await r.aclose()
            return True
        except Exception as e:
            logger.warning("Cache DELETE failed key=%s: %s", key, e)
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a glob pattern.
        Use sparingly — SCAN is O(N) over the keyspace.
        e.g. await cache.invalidate_pattern("dashboard:tenant_1:*")
        """
        deleted = 0
        try:
            r    = await self._client()
            keys = await r.keys(pattern)
            if keys:
                deleted = await r.delete(*keys)
            await r.aclose()
        except Exception as e:
            logger.warning("Cache INVALIDATE_PATTERN failed pattern=%s: %s", pattern, e)
        return deleted

    # ------------------------------------------------------------------
    # Helpers for common cache keys
    # ------------------------------------------------------------------
    @staticmethod
    def dashboard_key(tenant_id: int, user_id: int) -> str:
        return f"dashboard:{tenant_id}:{user_id}"

    @staticmethod
    def fx_rate_key(from_currency: str, to_currency: str) -> str:
        return f"fx_rate:{from_currency}:{to_currency}"

    @staticmethod
    def pricing_key(item_id: int) -> str:
        return f"pricing:{item_id}"

    @staticmethod
    def container_key(container_id: int) -> str:
        return f"container:{container_id}"