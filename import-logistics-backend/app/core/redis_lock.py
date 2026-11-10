
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


class LockNotAcquiredError(Exception):
    """Raised when a distributed Redis lock cannot be acquired."""


# ------------------------------------------------------------------------------
# Async lock (FastAPI / async services)
# ------------------------------------------------------------------------------
class RedisLock:
    def __init__(
        self,
        name: str,
        ttl_seconds: int = 60,
    ):
        self.name = f"lock:{name}"
        self.ttl_seconds = ttl_seconds
        self._token = str(uuid.uuid4())
        self._redis: aioredis.Redis | None = None

    async def __aenter__(self) -> "RedisLock":
        self._redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

        try:
            acquired = await self._redis.set(
                self.name,
                self._token,
                nx=True,
                ex=self.ttl_seconds,
            )

            if not acquired:
                raise LockNotAcquiredError(
                    f"Could not acquire lock: {self.name}"
                )

            logger.debug("Lock acquired: %s", self.name)

            return self

        except Exception:
            await self._redis.close()
            self._redis = None
            raise

    async def __aexit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
    ) -> None:
        if self._redis is None:
            return

        try:
            # Release only if we still own the lock.
            # Lua guarantees atomicity.
            lua = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """

            await self._redis.eval(
                lua,
                1,
                self.name,
                self._token,
            )

            logger.debug("Lock released: %s", self.name)

        finally:
            await self._redis.close()
            self._redis = None


# ------------------------------------------------------------------------------
# Sync lock (Celery workers — synchronous context)
# ------------------------------------------------------------------------------
class SyncRedisLock:
    def __init__(
        self,
        name: str,
        ttl_seconds: int = 60,
    ):
        self.name = f"lock:{name}"
        self.ttl_seconds = ttl_seconds
        self._token = str(uuid.uuid4())
        self._redis: redis.Redis | None = None

    def __enter__(self) -> "SyncRedisLock":
        self._redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

        try:
            acquired = self._redis.set(
                self.name,
                self._token,
                nx=True,
                ex=self.ttl_seconds,
            )

            if not acquired:
                raise LockNotAcquiredError(
                    f"Could not acquire lock: {self.name}"
                )

            logger.debug("Sync lock acquired: %s", self.name)

            return self

        except Exception:
            self._redis.close()
            self._redis = None
            raise

    def __exit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
    ) -> None:
        if self._redis is None:
            return

        try:
            lua = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """

            self._redis.eval(
                lua,
                1,
                self.name,
                self._token,
            )

            logger.debug("Sync lock released: %s", self.name)

        finally:
            self._redis.close()
            self._redis = None
