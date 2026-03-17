# app/core/redis_lock.py
"""
Distributed Redis lock using SET NX PX pattern.
Prevents concurrent execution of critical Celery tasks
(e.g. update_fx_rates, update_all_tracking).

Usage:
    async with RedisLock("fx_update", ttl_seconds=3300):
        # only one worker runs this block at a time
        ...

    # Sync version for Celery workers (non-async context):
    with SyncRedisLock("fx_update", ttl_seconds=3300):
        ...
"""
import uuid
import logging
import redis
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Async lock (FastAPI / async services)
# ------------------------------------------------------------------------------
class RedisLock:
    def __init__(self, name: str, ttl_seconds: int = 60):
        self.name        = f"lock:{name}"
        self.ttl_seconds = ttl_seconds
        self._token      = str(uuid.uuid4())
        self._redis: aioredis.Redis | None = None

    async def __aenter__(self) -> "RedisLock":
        self._redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        acquired = await self._redis.set(
            self.name, self._token,
            nx=True,                         # only set if key does NOT exist
            ex=self.ttl_seconds,
        )
        if not acquired:
            await self._redis.aclose()
            raise LockNotAcquiredError(f"Could not acquire lock: {self.name}")
        logger.debug("Lock acquired: %s", self.name)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._redis:
            # Only release if we still own the lock (Lua script for atomicity)
            lua = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await self._redis.eval(lua, 1, self.name, self._token)
            await self._redis.aclose()
            logger.debug("Lock released: %s", self.name)


# ------------------------------------------------------------------------------
# Sync lock (Celery workers — synchronous context)
# ------------------------------------------------------------------------------
class SyncRedisLock:
    def __init__(self, name: str, ttl_seconds: int = 60):
        self.name        = f"lock:{name}"
        self.ttl_seconds = ttl_seconds
        self._token      = str(uuid.uuid4())
        self._redis: redis.Redis | None = None

    def __enter__(self) -> "SyncRedisLock":
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        acquired = self._redis.set(
            self.name, self._token,
            nx=True,
            ex=self.ttl_seconds,
        )
        if not acquired:
            self._redis.close()
            raise LockNotAcquiredError(f"Could not acquire lock: {self.name}")
        logger.debug("Sync lock acquired: %s", self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._redis:
            lua = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            self._redis.eval(lua, 1, self.name, self._token)
            self._redis.close()
            logger.debug("Sync lock released: %s", self.name)


class LockNotAcquiredError(Exception):
    """Raised when a distributed lock cannot be acquired."""
    pass