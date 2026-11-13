# app/tests/test_tracking.py
"""HTTP-level tests for shipment tracking. The Celery task is replaced by a recorder, so no
broker is needed; these tests check WHO may queue an update and for WHICH container."""
import pytest

from app.tests.api_helpers import API, NO_TOKEN, make_container

pytestmark = pytest.mark.asyncio


@pytest.fixture
def queued(monkeypatch):
    """Replace the Celery call with a list that records what would have been queued."""
    from app.workers import tracking_worker
    calls: list[dict] = []
    monkeypatch.setattr(tracking_worker.update_container_tracking, "apply_async",
                        lambda *a, **kw: calls.append({"args": kw.get("args"), "queue": kw.get("queue")}))
    return calls


async def test_an_allowed_user_queues_an_update_for_their_own_container(world, queued):
    box = await make_container(world.client, world.h["admin_a"])
    r = await world.client.post(f"{API}/tracking/{box['id']}/update", headers=world.h["admin_a"])
    assert r.status_code == 200, r.text
    assert queued == [{"args": [box["id"], world.org_a], "queue": "tracking_queue"}]


async def test_viewers_cannot_queue_updates(world, queued):
    box = await make_container(world.client, world.h["admin_a"])
    r = await world.client.post(f"{API}/tracking/{box['id']}/update", headers=world.h["viewer_a"])
    assert r.status_code == 403 and queued == []


async def test_other_organisations_cannot_queue_updates_for_my_container(world, queued):
    box = await make_container(world.client, world.h["admin_a"])
    r = await world.client.post(f"{API}/tracking/{box['id']}/update", headers=world.h["admin_b"])
    assert r.status_code == 404 and queued == []


async def test_a_clerk_cannot_queue_an_update_for_a_colleagues_container(world, queued):
    box = await make_container(world.client, world.h["clerk2_a"])
    r = await world.client.post(f"{API}/tracking/{box['id']}/update", headers=world.h["clerk_a"])
    assert r.status_code == 404 and queued == []


async def test_unknown_container_is_a_404_and_nothing_is_queued(world, queued):
    r = await world.client.post(f"{API}/tracking/999999/update", headers=world.h["admin_a"])
    assert r.status_code == 404 and queued == []


async def test_history_is_private_to_the_organisation(world):
    box = await make_container(world.client, world.h["admin_a"])
    mine = await world.client.get(f"{API}/tracking/{box['id']}/history", headers=world.h["admin_a"])
    theirs = await world.client.get(f"{API}/tracking/{box['id']}/history", headers=world.h["admin_b"])
    assert mine.status_code == 200
    assert theirs.status_code == 200 and theirs.json() == []     # no data leaks across organisations


async def test_tracking_requires_a_login(world):
    assert (await world.client.get(f"{API}/tracking/1/history")).status_code in NO_TOKEN
    assert (await world.client.get(f"{API}/tracking/1/status")).status_code in NO_TOKEN
    assert (await world.client.post(f"{API}/tracking/1/update")).status_code in NO_TOKEN