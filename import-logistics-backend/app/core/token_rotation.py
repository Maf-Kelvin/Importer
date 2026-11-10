# app/core/token_rotation.py
"""Atomic one-time use of a token (standard library only, so it is unit-tested).

Refresh tokens rotate: each may be exchanged exactly once. Checking "is it revoked?" and then
revoking it as two separate steps lets two simultaneous requests both pass the check. A single
`SET key value NX EX ttl` is atomic in Redis, so exactly one caller gets True.
"""
from typing import Any


async def consume_once(client: Any, key: str, ttl_seconds: int) -> bool:
    """True only for the FIRST caller for this key; every later caller gets False."""
    return bool(await client.set(key, "1", nx=True, ex=max(int(ttl_seconds), 1)))
