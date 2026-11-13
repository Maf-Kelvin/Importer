# app/tests/test_auth.py
"""HTTP-level tests for sign-in, sessions and token binding (real app, real Postgres)."""
import pytest
from sqlalchemy import update

from app.tests.api_helpers import API, NO_TOKEN, PASSWORD, bearer, create_user

pytestmark = pytest.mark.asyncio

NEW_PASSWORD = "New-Passw0rd-456!"


async def login(client, username, password=PASSWORD, **headers):
    return await client.post(f"{API}/auth/login", data={"username": username, "password": password}, headers=headers)


async def test_login_returns_tokens_and_the_token_works(world):
    r = await login(world.client, "admin_a")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer" and body["access_token"] and body["refresh_token"]
    me = await world.client.get(f"{API}/users/me", headers={"Authorization": "Bearer " + body["access_token"]})
    assert me.status_code == 200 and me.json()["username"] == "admin_a"


async def test_wrong_password_and_unknown_user_look_the_same(world):
    bad_pw = await login(world.client, "admin_a", "not-the-password-1")
    unknown = await login(world.client, "nobody_here")
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.json()["detail"] == unknown.json()["detail"]


async def test_inactive_user_cannot_sign_in(world):
    await create_user(world.sessions, world.org_a, "sleeper", "clerk", active=False)
    assert (await login(world.client, "sleeper")).status_code in (401, 403)


async def test_requests_without_a_valid_token_are_rejected(world):
    assert (await world.client.get(f"{API}/users/me")).status_code in NO_TOKEN
    assert (await world.client.get(f"{API}/users/me", headers={"Authorization": "Bearer garbage"})).status_code == 401


async def test_deactivated_user_loses_access_immediately(world):
    from app.models.user import User
    async with world.sessions() as s, s.begin():
        await s.execute(update(User).where(User.id == world.u["clerk_a"].id).values(is_active=False))
    assert (await world.client.get(f"{API}/users/me", headers=world.h["clerk_a"])).status_code in (400, 401, 403)


async def test_registration_is_closed_by_default(world):
    r = await world.client.post(f"{API}/auth/register", json={
        "email": "x@example.com", "username": "x_user", "first_name": "X", "last_name": "Y",
        "password": PASSWORD, "role": "viewer"})
    assert r.status_code == 403


# ---------------------------------------------------------------- lockout (per username AND ip)
async def test_lockout_applies_to_the_attacker_not_to_the_real_user(world):
    from app.core.config import settings
    attacker = world.make_client("198.51.100.7")
    for _ in range(settings.MAX_LOGIN_ATTEMPTS):
        assert (await login(attacker, "admin_a", "wrong-password-1")).status_code == 401
    # The attacker is now locked out, even with the right password...
    assert (await login(attacker, "admin_a")).status_code == 401
    # ...but the real user, at another address, is not.
    assert (await login(world.make_client("203.0.113.99"), "admin_a")).status_code == 200


# ---------------------------------------------------------------- refresh tokens
async def test_refresh_rotates_and_the_old_token_dies(world):
    first = (await login(world.client, "admin_a")).json()
    r = await world.client.post(f"{API}/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 200, r.text
    second = r.json()
    assert second["access_token"] and second["refresh_token"] != first["refresh_token"]
    replay = await world.client.post(f"{API}/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401


async def test_an_access_token_cannot_be_used_as_a_refresh_token(world):
    tokens = (await login(world.client, "admin_a")).json()
    r = await world.client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401


async def test_a_refresh_token_cannot_be_used_as_an_access_token(world):
    tokens = (await login(world.client, "admin_a")).json()
    r = await world.client.get(f"{API}/users/me", headers={"Authorization": "Bearer " + tokens["refresh_token"]})
    assert r.status_code == 401


async def test_cookie_mode_keeps_the_refresh_token_out_of_the_body(world):
    r = await login(world.client, "admin_a", **{"X-Auth-Mode": "cookie"})
    assert r.status_code == 200 and r.json()["refresh_token"] is None
    cookie = r.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    ok = await world.client.post(f"{API}/auth/refresh", headers={"X-Auth-Mode": "cookie"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    # The cookie alone is not enough: the custom header is the CSRF guard.
    assert (await world.client.post(f"{API}/auth/refresh")).status_code == 401


async def test_logout_revokes_the_refresh_token(world):
    tokens = (await login(world.client, "admin_a")).json()
    out = await world.client.post(f"{API}/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 200
    assert (await world.client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401


# ---------------------------------------------------------------- token binding
async def test_changing_the_password_ends_every_existing_session(world):
    tokens = (await login(world.client, "admin_a")).json()
    old_access = {"Authorization": "Bearer " + tokens["access_token"]}
    change = await world.client.put(f"{API}/users/me", headers=old_access, json={"password": NEW_PASSWORD})
    assert change.status_code == 200, change.text

    assert (await world.client.get(f"{API}/users/me", headers=old_access)).status_code == 401
    assert (await world.client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401
    assert (await login(world.client, "admin_a", PASSWORD)).status_code == 401
    assert (await login(world.make_client("203.0.113.55"), "admin_a", NEW_PASSWORD)).status_code == 200


async def test_renaming_an_account_does_not_end_its_session(world):
    r = await world.client.put(f"{API}/users/me", headers=world.h["admin_a"], json={"username": "renamed_admin"})
    assert r.status_code == 200, r.text
    me = await world.client.get(f"{API}/users/me", headers=world.h["admin_a"])
    assert me.status_code == 200 and me.json()["username"] == "renamed_admin"


async def test_forged_or_stale_tokens_are_rejected(world):
    from app.models.user import User
    # Real accounts never share a password hash (bcrypt salts each one), but the shared test
    # fixtures do. Give the viewer a different hash so "someone else's id" is a meaningful check.
    async with world.sessions() as s, s.begin():
        await s.execute(update(User).where(User.id == world.u["viewer_a"].id).values(hashed_password="a-different-hash"))
    user = world.u["admin_a"]
    ok = await world.client.get(f"{API}/users/me", headers=bearer(user))
    assert ok.status_code == 200
    forged = {
        "wrong password fingerprint": bearer(user, pwf="0" * 16),
        "no password fingerprint": bearer(user, pwf=None),
        "username as subject (old format)": bearer(user, subject=user.username),
        "wrong organisation": bearer(user, tenant_id=user.tenant_id + 1000),
        "someone else's id": bearer(user, subject=str(world.u["viewer_a"].id)),
    }
    for label, headers in forged.items():
        r = await world.client.get(f"{API}/users/me", headers=headers)
        assert r.status_code == 401, f"{label}: {r.status_code}"