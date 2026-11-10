# app/core/idempotency.py
"""
Idempotency core: request fingerprinting and the claim/complete/release
state machine, with an in-memory store (tests) and a Redis store (production).

How it works
------------
1. A request with an ``Idempotency-Key`` tries to *claim* the key atomically
   (Redis ``SET NX``). Only one of several simultaneous requests wins.
2. Winner runs the endpoint, then *completes* the key with the stored response.
3. Same key + same request   -> stored response is replayed.
   Same key + other request  -> rejected (422).
   Same key, still running   -> rejected (409, client should retry shortly).
4. If the endpoint fails (non-2xx or exception) the key is *released* so the
   client may retry safely.

Limits (be honest about them):
  * Redis is the only store. If it loses data, a duplicate can slip through,
    so money-moving operations must ALSO have a database unique constraint.
  * If the process dies between "endpoint committed" and "key completed",
    the claim expires after ``lock_ttl`` and a retry would run again.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional

_KEY_RE = re.compile(r"^[A-Za-z0-9_\-.:]{8,128}$")


def validate_key(raw: str) -> str:
    """Idempotency keys are 8-128 chars of letters, digits and _-.: (UUIDs fit)."""
    if not _KEY_RE.match(raw or ""):
        raise ValueError(
            "Idempotency-Key must be 8-128 characters: letters, digits, _ - . :"
        )
    return raw


def fingerprint(method: str, path: str, query: str, body: bytes) -> str:
    h = hashlib.sha256()
    for part in (method.upper().encode(), path.encode(), query.encode()):
        h.update(part)
        h.update(b"\x00")
    h.update(body)
    return h.hexdigest()


def storage_key(identity: str, key: str) -> str:
    """Namespaced per authenticated user; the client key is hashed."""
    digest = hashlib.sha256(key.encode()).hexdigest()[:40]
    return f"idem:{identity}:{digest}"


def encode_response(status: int, content_type: Optional[str], body: bytes) -> dict:
    return {
        "status": status,
        "content_type": content_type,
        "body_b64": base64.b64encode(body).decode(),
    }


def decode_response(record: dict) -> tuple[int, Optional[str], bytes]:
    return (
        int(record["status"]),
        record.get("content_type"),
        base64.b64decode(record["body_b64"]),
    )


@dataclass(frozen=True)
class ClaimOutcome:
    status: str                      # claimed | in_progress | replay | mismatch
    record: Optional[dict] = None    # stored response when status == "replay"


def classify(existing: dict, fp: str) -> ClaimOutcome:
    if existing.get("fingerprint") != fp:
        return ClaimOutcome("mismatch")
    if existing.get("state") == "completed":
        return ClaimOutcome("replay", existing.get("response"))
    return ClaimOutcome("in_progress")


class IdempotencyStore:
    async def claim(self, key: str, fp: str, owner: str, lock_ttl: int) -> ClaimOutcome:
        raise NotImplementedError

    async def complete(self, key: str, fp: str, owner: str, response: dict, ttl: int) -> bool:
        raise NotImplementedError

    async def release(self, key: str, owner: str) -> bool:
        raise NotImplementedError


# ------------------------------------------------------------------------------
# In-memory store (unit tests, local experiments)
# ------------------------------------------------------------------------------
class InMemoryIdempotencyStore(IdempotencyStore):
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._data: dict[str, tuple[dict, float]] = {}

    def _get(self, key: str) -> Optional[dict]:
        item = self._data.get(key)
        if item is None:
            return None
        record, expires = item
        if expires <= self._clock():
            del self._data[key]
            return None
        return record

    async def claim(self, key, fp, owner, lock_ttl):
        existing = self._get(key)
        if existing is None:
            self._data[key] = (
                {"state": "processing", "fingerprint": fp, "owner": owner},
                self._clock() + lock_ttl,
            )
            return ClaimOutcome("claimed")
        return classify(existing, fp)

    async def complete(self, key, fp, owner, response, ttl):
        existing = self._get(key)
        if not existing or existing.get("owner") != owner or existing.get("state") != "processing":
            return False
        self._data[key] = (
            {"state": "completed", "fingerprint": fp, "owner": owner, "response": response},
            self._clock() + ttl,
        )
        return True

    async def release(self, key, owner):
        existing = self._get(key)
        if existing and existing.get("owner") == owner and existing.get("state") == "processing":
            del self._data[key]
            return True
        return False


# ------------------------------------------------------------------------------
# Redis store (production). `client_factory` returns a redis.asyncio client
# created with decode_responses=True.
# ------------------------------------------------------------------------------
_LUA_COMPLETE = """
local v = redis.call('GET', KEYS[1])
if not v then return 0 end
local d = cjson.decode(v)
if d.owner ~= ARGV[1] or d.state ~= 'processing' then return 0 end
redis.call('SET', KEYS[1], ARGV[2], 'EX', tonumber(ARGV[3]))
return 1
"""

_LUA_RELEASE = """
local v = redis.call('GET', KEYS[1])
if not v then return 0 end
local d = cjson.decode(v)
if d.owner ~= ARGV[1] or d.state ~= 'processing' then return 0 end
return redis.call('DEL', KEYS[1])
"""


class RedisIdempotencyStore(IdempotencyStore):
    def __init__(self, client_factory: Callable[[], Any]) -> None:
        self._client_factory = client_factory

    async def claim(self, key, fp, owner, lock_ttl):
        client = self._client_factory()
        record = {"state": "processing", "fingerprint": fp, "owner": owner}
        for _ in range(3):  # the key may expire between SET NX and GET
            if await client.set(key, json.dumps(record), nx=True, ex=lock_ttl):
                return ClaimOutcome("claimed")
            raw = await client.get(key)
            if raw is not None:
                return classify(json.loads(raw), fp)
        return ClaimOutcome("in_progress")

    async def complete(self, key, fp, owner, response, ttl):
        client = self._client_factory()
        record = {"state": "completed", "fingerprint": fp, "owner": owner, "response": response}
        done = await client.eval(_LUA_COMPLETE, 1, key, owner, json.dumps(record), ttl)
        return bool(done)

    async def release(self, key, owner):
        client = self._client_factory()
        return bool(await client.eval(_LUA_RELEASE, 1, key, owner))


def new_owner() -> str:
    return uuid.uuid4().hex


# ------------------------------------------------------------------------------
# PostgreSQL store (default, production). The UNIQUE constraint on `key` is the
# guarantee, so a Redis flush or restart can never let a duplicate through.
# Every operation runs in its own short transaction so the claim is committed -
# and visible to concurrent requests - before the endpoint starts.
# ------------------------------------------------------------------------------
class PostgresIdempotencyStore(IdempotencyStore):
    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self._session_factory = session_factory

    async def claim(self, key, fp, owner, lock_ttl):
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import select, update
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from app.models.idempotency import IdempotencyKey as Row

        for _ in range(3):
            now = datetime.now(timezone.utc)
            expires = now + timedelta(seconds=lock_ttl)
            async with self._session_factory() as session:
                async with session.begin():
                    inserted = await session.execute(
                        pg_insert(Row)
                        .values(key=key, fingerprint=fp, state="processing", owner=owner,
                                response=None, expires_at=expires)
                        .on_conflict_do_nothing(index_elements=["key"])
                    )
                    if inserted.rowcount == 1:
                        return ClaimOutcome("claimed")
                    # Row exists. If it has expired (crashed request / old record) take it over.
                    taken = await session.execute(
                        update(Row)
                        .where(Row.key == key, Row.expires_at < now)
                        .values(state="processing", fingerprint=fp, owner=owner,
                                response=None, expires_at=expires)
                    )
                    if taken.rowcount == 1:
                        return ClaimOutcome("claimed")
                    row = (await session.execute(select(Row).where(Row.key == key))).scalar_one_or_none()
                    if row is not None:
                        return classify(
                            {"state": row.state, "fingerprint": row.fingerprint,
                             "owner": row.owner, "response": row.response},
                            fp,
                        )
            # the row vanished between the INSERT and the SELECT (released): try again
        return ClaimOutcome("in_progress")

    async def complete(self, key, fp, owner, response, ttl):
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import update

        from app.models.idempotency import IdempotencyKey as Row

        async with self._session_factory() as session:
            async with session.begin():
                done = await session.execute(
                    update(Row)
                    .where(Row.key == key, Row.owner == owner, Row.state == "processing")
                    .values(state="completed", response=response,
                            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl))
                )
                return done.rowcount == 1

    async def release(self, key, owner):
        from sqlalchemy import delete

        from app.models.idempotency import IdempotencyKey as Row

        async with self._session_factory() as session:
            async with session.begin():
                gone = await session.execute(
                    delete(Row).where(Row.key == key, Row.owner == owner, Row.state == "processing")
                )
                return gone.rowcount == 1

