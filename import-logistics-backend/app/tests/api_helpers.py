# app/tests/api_helpers.py
"""Shared helpers for the HTTP-level tests (auth, containers, items, pricing, tracking).

Kept free of app imports at module level so that merely importing this file never needs
the database or Redis; everything app-related is imported inside the functions."""
from __future__ import annotations

import fnmatch
from functools import lru_cache
from types import SimpleNamespace

PASSWORD = "Test-Passw0rd-123!"
API = "/api/v1"
# A request with NO token: older FastAPI answers 403, newer answers 401. Both mean "not signed in".
NO_TOKEN = (401, 403)


@lru_cache(maxsize=1)
def password_hash() -> str:
    """bcrypt is deliberately slow, so hash the shared test password once."""
    from app.core.security import get_password_hash
    return get_password_hash(PASSWORD)


class FakeRedis:
    """Just enough of redis.asyncio for the app's login lockout, token blacklist and cache.
    Expiry times are recorded but not enforced: no test here runs long enough to need them."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, nx=False, ex=None, **_):
        if nx and key in self.data:
            return None
        self.data[key] = value
        if ex:
            self.ttls[key] = ex
        return True

    async def setex(self, key, ttl, value):
        self.data[key] = value
        self.ttls[key] = ttl
        return True

    async def exists(self, *keys):
        return sum(1 for k in keys if k in self.data)

    async def incr(self, key):
        self.data[key] = str(int(self.data.get(key, 0)) + 1)
        return int(self.data[key])

    async def expire(self, key, ttl):
        self.ttls[key] = ttl
        return True

    async def delete(self, *keys):
        return sum(1 for k in keys if self.data.pop(k, None) is not None)

    async def keys(self, pattern="*"):
        return [k for k in self.data if fnmatch.fnmatch(k, pattern)]

    async def ping(self):
        return True


async def create_org(sessions, slug: str) -> int:
    from app.models.organization import Organization
    async with sessions() as s, s.begin():
        org = Organization(name=slug, slug=slug)
        s.add(org)
        await s.flush()
        return org.id


async def create_user(sessions, tenant_id: int, username: str, role: str, *, active: bool = True):
    from app.models.user import User, UserRole
    async with sessions() as s, s.begin():
        user = User(
            tenant_id=tenant_id, email=f"{username}@example.com", username=username,
            first_name=username.title(), last_name="Test", hashed_password=password_hash(),
            role=UserRole(role), is_active=active,
        )
        s.add(user)
        await s.flush()
        return SimpleNamespace(
            id=user.id, tenant_id=tenant_id, username=username,
            role=user.role, hashed_password=user.hashed_password,
        )


def bearer(user, **overrides) -> dict:
    """Authorization header with a correctly signed access token for `user` (no login needed).
    Keyword overrides let a test forge a bad token: subject=, tenant_id=, pwf=."""
    from app.core import security
    from app.core.token_claims import password_fingerprint
    claims = dict(
        subject=str(user.id), tenant_id=user.tenant_id, role=user.role.value,
        pwf=password_fingerprint(user.hashed_password),
    )
    claims.update(overrides)
    return {"Authorization": "Bearer " + security.create_access_token(**claims)}


# ---- small API helpers that assert the happy path, so tests can focus on what they check ----
async def make_container(client, headers, name="Box", **extra) -> dict:
    body = {"name": name, "container_type": "40ft", "allocation_method": "weight_based", **extra}
    r = await client.post(f"{API}/containers/", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def add_item(client, headers, container_id, name="item", price="10.00", weight="1.000") -> dict:
    body = {"container_id": container_id, "name": name, "category": "other", "condition": "new",
            "purchase_price": price, "purchase_currency": "USD"}
    if weight is not None:          # weight=None leaves it out, as the app does when it is unknown
        body["weight"] = weight
    r = await client.post(f"{API}/items/", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def add_expense(client, headers, container_id, amount="100.00", kind="shipping_fee") -> dict:
    r = await client.post(f"{API}/expenses/", headers=headers, json={
        "container_id": container_id, "expense_type": kind, "amount": amount, "currency": "USD"})
    assert r.status_code == 201, r.text
    return r.json()