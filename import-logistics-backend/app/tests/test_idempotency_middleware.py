# app/tests/test_idempotency_middleware.py
"""HTTP-level tests for the idempotency middleware (in-memory store, no Redis)."""
import asyncio

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from app.core import security
from app.core.idempotency import InMemoryIdempotencyStore
from app.middleware.idempotency_middleware import IdempotencyMiddleware

pytestmark = pytest.mark.asyncio
KEY = "3f2b8c1e-0a4d-4e7a-9d55-1b2c3d4e5f60"


def make_app(calls: list):
    app = FastAPI()
    app.add_middleware(IdempotencyMiddleware, store=InMemoryIdempotencyStore())

    @app.post("/things")
    async def create(request: Request):
        body = await request.json()
        calls.append(body)
        await asyncio.sleep(0.05)
        return {"n": len(calls), "echo": body}

    @app.post("/bad")
    async def bad(request: Request):
        calls.append(await request.json())
        return JSONResponse({"detail": "nope"}, status_code=400)

    return app


def auth(user="alice", tenant=1):
    token = security.create_access_token(user, tenant_id=tenant, role="admin")
    return {"Authorization": f"Bearer {token}"}


def client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_same_key_same_body_is_replayed():
    calls = []
    async with client(make_app(calls)) as c:
        h = {**auth(), "Idempotency-Key": KEY}
        first = await c.post("/things", json={"a": 1}, headers=h)
        second = await c.post("/things", json={"a": 1}, headers=h)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert second.headers.get("idempotent-replayed") == "true"
    assert len(calls) == 1


async def test_same_key_different_body_is_rejected():
    calls = []
    async with client(make_app(calls)) as c:
        h = {**auth(), "Idempotency-Key": KEY}
        await c.post("/things", json={"a": 1}, headers=h)
        again = await c.post("/things", json={"a": 2}, headers=h)
    assert again.status_code == 422
    assert len(calls) == 1


async def test_simultaneous_duplicates_execute_once():
    calls = []
    async with client(make_app(calls)) as c:
        h = {**auth(), "Idempotency-Key": KEY}
        results = await asyncio.gather(
            *[c.post("/things", json={"a": 1}, headers=h) for _ in range(5)]
        )
    assert len(calls) == 1
    assert {r.status_code for r in results} <= {200, 409}
    assert sum(r.status_code == 200 and "idempotent-replayed" not in r.headers for r in results) == 1


async def test_keys_are_not_shared_between_users():
    calls = []
    async with client(make_app(calls)) as c:
        await c.post("/things", json={"a": 1}, headers={**auth("alice"), "Idempotency-Key": KEY})
        other = await c.post("/things", json={"a": 1}, headers={**auth("bob"), "Idempotency-Key": KEY})
    assert "idempotent-replayed" not in other.headers
    assert len(calls) == 2


async def test_failed_request_can_be_retried():
    calls = []
    async with client(make_app(calls)) as c:
        h = {**auth(), "Idempotency-Key": KEY}
        await c.post("/bad", json={"a": 1}, headers=h)
        await c.post("/bad", json={"a": 1}, headers=h)
    assert len(calls) == 2


async def test_requests_without_valid_token_skip_idempotency():
    calls = []
    async with client(make_app(calls)) as c:
        h = {"Idempotency-Key": KEY}
        await c.post("/things", json={"a": 1}, headers=h)
        await c.post("/things", json={"a": 1}, headers=h)
    assert len(calls) == 2


async def test_malformed_key_is_a_400():
    async with client(make_app([])) as c:
        r = await c.post("/things", json={}, headers={**auth(), "Idempotency-Key": "short"})
    assert r.status_code == 400
