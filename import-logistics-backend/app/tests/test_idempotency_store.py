# app/tests/test_idempotency_store.py
import asyncio

import pytest

from app.core.idempotency import (
    InMemoryIdempotencyStore, decode_response, encode_response,
    fingerprint, new_owner, storage_key, validate_key,
)


def run(coro):
    return asyncio.run(coro)


def test_key_validation():
    assert validate_key("3f2b8c1e-0a4d-4e7a-9d55-1b2c3d4e5f60")
    for bad in ["", "short", "has space in it", "x" * 129, "bad/slash/key1"]:
        with pytest.raises(ValueError):
            validate_key(bad)


def test_fingerprint_changes_with_body_path_method_query():
    base = fingerprint("POST", "/a", "", b"{}")
    assert base == fingerprint("post", "/a", "", b"{}")
    assert base != fingerprint("POST", "/a", "", b'{"x":1}')
    assert base != fingerprint("POST", "/b", "", b"{}")
    assert base != fingerprint("PUT", "/a", "", b"{}")
    assert base != fingerprint("POST", "/a", "q=1", b"{}")


def test_keys_are_namespaced_per_user():
    k = "3f2b8c1e-0a4d-4e7a-9d55-1b2c3d4e5f60"
    assert storage_key("1:alice", k) != storage_key("1:bob", k)
    assert storage_key("1:alice", k) != storage_key("2:alice", k)


def test_only_one_of_two_simultaneous_requests_wins():
    async def scenario():
        store = InMemoryIdempotencyStore()
        results = await asyncio.gather(*[
            store.claim("k", "fp", new_owner(), 60) for _ in range(10)
        ])
        statuses = [r.status for r in results]
        assert statuses.count("claimed") == 1
        assert statuses.count("in_progress") == 9
    run(scenario())


def test_completed_request_is_replayed():
    async def scenario():
        store = InMemoryIdempotencyStore()
        owner = new_owner()
        assert (await store.claim("k", "fp", owner, 60)).status == "claimed"
        resp = encode_response(201, "application/json", b'{"id": 1}')
        assert await store.complete("k", "fp", owner, resp, 3600)
        again = await store.claim("k", "fp", new_owner(), 60)
        assert again.status == "replay"
        assert decode_response(again.record) == (201, "application/json", b'{"id": 1}')
    run(scenario())


def test_same_key_with_different_request_is_a_mismatch():
    async def scenario():
        store = InMemoryIdempotencyStore()
        await store.claim("k", "fp-1", new_owner(), 60)
        assert (await store.claim("k", "fp-2", new_owner(), 60)).status == "mismatch"
    run(scenario())


def test_failed_request_releases_the_key_so_retry_can_run():
    async def scenario():
        store = InMemoryIdempotencyStore()
        owner = new_owner()
        await store.claim("k", "fp", owner, 60)
        assert await store.release("k", owner)
        assert (await store.claim("k", "fp", new_owner(), 60)).status == "claimed"
    run(scenario())


def test_only_the_owner_can_complete_or_release():
    async def scenario():
        store = InMemoryIdempotencyStore()
        owner = new_owner()
        await store.claim("k", "fp", owner, 60)
        other = new_owner()
        assert not await store.release("k", other)
        assert not await store.complete("k", "fp", other, encode_response(200, None, b""), 60)
    run(scenario())


def test_crashed_request_frees_the_key_after_lock_ttl():
    async def scenario():
        now = [0.0]
        store = InMemoryIdempotencyStore(clock=lambda: now[0])
        await store.claim("k", "fp", new_owner(), 30)
        assert (await store.claim("k", "fp", new_owner(), 30)).status == "in_progress"
        now[0] = 31
        assert (await store.claim("k", "fp", new_owner(), 30)).status == "claimed"
    run(scenario())
