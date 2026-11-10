
# app/core/redis_clients.py
"""
Shared async Redis clients (one connection pool each, per event loop).

Two logical Redis roles, so cache eviction can never destroy critical state:
  * state - Celery broker, locks, idempotency keys, token blacklist
            (run with maxmemory-policy noeviction)
  * cache - dashboards, FX rates (run with allkeys-lru; safe to lose)

Clients are keyed by the running event loop because a redis.asyncio client
must not be shared across loops (Celery tasks run their own loop).
"""

from __future__ import annotations

import asyncio
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_clients: dict[
    str,
    tuple[asyncio.AbstractEventLoop, aioredis.Redis],
] = {}


def _get(kind: str, url: str) -> aioredis.Redis:
    loop = asyncio.get_running_loop()

    entry = _clients.get(kind)

    if (
        entry is not None
        and entry[0] is loop
        and not loop.is_closed()
    ):
        return entry[1]

    client = aioredis.from_url(
        url,
        decode_responses=True,
        max_connections=50,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )

    _clients[kind] = (loop, client)

    return client


def get_state_redis() -> aioredis.Redis:
    return _get("state", settings.REDIS_URL)


def get_cache_redis() -> aioredis.Redis:
    return _get(
        "cache",
        settings.CACHE_REDIS_URL or settings.REDIS_URL,
    )


async def close_redis_clients() -> None:
    """
    Close all shared Redis clients.

    Uses close(), supported by redis-py 4.6.0.
    """

    for kind, (_, client) in list(_clients.items()):
        try:
            await client.close()

        except Exception as exc:
            logger.warning(
                "Error closing %s Redis client: %s",
                kind,
                exc,
            )

    _clients.clear()
