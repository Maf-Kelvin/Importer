# app/tests/conftest.py
"""Fixtures for the HTTP-level tests.

They drive the REAL FastAPI app in-process (httpx ASGITransport) against a REAL PostgreSQL
database and skip unless TEST_DATABASE_URL is set (CI sets it). Redis is replaced by an
in-memory fake, so no Redis server is needed. Imports of the app stay inside fixtures so the
pure unit tests keep running without the web stack installed."""
import os
from types import SimpleNamespace

import pytest
import pytest_asyncio

from app.tests.api_helpers import FakeRedis, bearer, create_org, create_user

DB_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def env(monkeypatch):
    """App + clean database + fake Redis. Yields a namespace with a client factory."""
    if not DB_URL:
        pytest.skip("TEST_DATABASE_URL not set")

    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import app.core.database as dbmod
    from app.core.database import get_db
    from app.main import app
    from app.models import Base

    # NullPool: no connection outlives its test's event loop.
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def override_get_db():
        async with sessions() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    # The idempotency middleware (Postgres store) and workers look this up by name.
    monkeypatch.setattr(dbmod, "AsyncSessionLocal", sessions)

    redis = FakeRedis()
    monkeypatch.setattr("app.core.security.get_state_redis", lambda: redis)
    monkeypatch.setattr("app.services.cache_service.get_cache_redis", lambda: redis)
    monkeypatch.setattr("app.services.fx_service.get_cache_redis", lambda: redis)

    opened: list = []

    def make_client(ip: str = "203.0.113.10"):
        c = AsyncClient(transport=ASGITransport(app=app, client=(ip, 50000)), base_url="http://test")
        opened.append(c)
        return c

    try:
        yield SimpleNamespace(app=app, sessions=sessions, redis=redis, make_client=make_client)
    finally:
        for c in opened:
            await c.aclose()
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


@pytest_asyncio.fixture
async def world(env):
    """Two organisations. A has an admin, a manager, two clerks and a viewer; B has an admin.
    `w.h[name]` is a ready Authorization header, `w.u[name]` the user."""
    org_a = await create_org(env.sessions, "org-a")
    org_b = await create_org(env.sessions, "org-b")
    spec = {
        "admin_a": (org_a, "admin"), "manager_a": (org_a, "manager"),
        "clerk_a": (org_a, "clerk"), "clerk2_a": (org_a, "clerk"),
        "viewer_a": (org_a, "viewer"), "admin_b": (org_b, "admin"),
    }
    users = {name: await create_user(env.sessions, tid, name, role) for name, (tid, role) in spec.items()}
    return SimpleNamespace(
        client=env.make_client(), make_client=env.make_client, sessions=env.sessions,
        redis=env.redis, org_a=org_a, org_b=org_b,
        u=users, h={name: bearer(u) for name, u in users.items()},
    )