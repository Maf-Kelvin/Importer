# app/tests/test_idempotency_postgres.py
"""The durable idempotency store against REAL PostgreSQL.
Skipped unless TEST_DATABASE_URL is set (same as the allocation integration tests)."""
import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.idempotency import (
    PostgresIdempotencyStore, decode_response, encode_response, new_owner,
)
from app.models import Base
from app.models.idempotency import IdempotencyKey

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")]


@pytest_asyncio.fixture
async def setup():
    engine = create_async_engine(URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    yield PostgresIdempotencyStore(sessions), sessions
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def test_exactly_one_of_many_simultaneous_claims_wins(setup):
    store, _ = setup
    results = await asyncio.gather(*[store.claim("k", "fp", new_owner(), 60) for _ in range(20)])
    statuses = [r.status for r in results]
    assert statuses.count("claimed") == 1 and statuses.count("in_progress") == 19


async def test_completed_response_is_replayed(setup):
    store, _ = setup
    owner = new_owner()
    assert (await store.claim("k", "fp", owner, 60)).status == "claimed"
    assert await store.complete("k", "fp", owner, encode_response(201, "application/json", b'{"id":1}'), 3600)
    again = await store.claim("k", "fp", new_owner(), 60)
    assert again.status == "replay"
    assert decode_response(again.record) == (201, "application/json", b'{"id":1}')


async def test_different_request_with_same_key_is_a_mismatch(setup):
    store, _ = setup
    await store.claim("k", "fp-1", new_owner(), 60)
    assert (await store.claim("k", "fp-2", new_owner(), 60)).status == "mismatch"


async def test_release_allows_a_retry_and_only_the_owner_can_release(setup):
    store, _ = setup
    owner = new_owner()
    await store.claim("k", "fp", owner, 60)
    assert not await store.release("k", new_owner())
    assert await store.release("k", owner)
    assert (await store.claim("k", "fp", new_owner(), 60)).status == "claimed"


async def test_expired_claim_can_be_taken_over(setup):
    store, sessions = setup
    await store.claim("k", "fp", new_owner(), 60)
    async with sessions() as s, s.begin():
        await s.execute(update(IdempotencyKey).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    assert (await store.claim("k", "fp", new_owner(), 60)).status == "claimed"
