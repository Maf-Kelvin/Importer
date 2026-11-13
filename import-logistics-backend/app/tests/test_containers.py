# app/tests/test_containers.py
"""HTTP-level tests for containers: permissions, tenant isolation, idempotency, cost allocation."""
import uuid
from decimal import Decimal

import pytest

from app.tests.api_helpers import API, NO_TOKEN, add_expense, add_item, make_container

pytestmark = pytest.mark.asyncio


async def test_create_list_and_get(world):
    c = world.client
    box = await make_container(c, world.h["admin_a"], "First box")
    assert box["name"] == "First box" and box["id"]
    listing = (await c.get(f"{API}/containers/", headers=world.h["admin_a"])).json()
    assert listing["total"] == 1 and [x["id"] for x in listing["items"]] == [box["id"]]
    got = await c.get(f"{API}/containers/{box['id']}", headers=world.h["admin_a"])
    assert got.status_code == 200 and got.json()["id"] == box["id"]
    assert (await c.get(f"{API}/containers/999999", headers=world.h["admin_a"])).status_code == 404


async def test_who_may_create_containers(world):
    c = world.client
    payload = {"name": "x", "container_type": "20ft"}
    assert (await c.post(f"{API}/containers/", json=payload)).status_code in NO_TOKEN
    assert (await c.post(f"{API}/containers/", headers=world.h["viewer_a"], json=payload)).status_code == 403
    for role in ("clerk_a", "manager_a", "admin_a"):
        r = await c.post(f"{API}/containers/", headers=world.h[role], json=payload)
        assert r.status_code == 201, f"{role}: {r.text}"
    assert (await c.get(f"{API}/containers/", headers=world.h["viewer_a"])).status_code == 200


async def test_invalid_input_is_a_422(world):
    c = world.client
    bad_type = await c.post(f"{API}/containers/", headers=world.h["admin_a"], json={"name": "x", "container_type": "99ft"})
    no_name = await c.post(f"{API}/containers/", headers=world.h["admin_a"], json={"container_type": "20ft"})
    assert bad_type.status_code == 422 and no_name.status_code == 422


async def test_other_organisations_see_nothing(world):
    c = world.client
    box = await make_container(c, world.h["admin_a"])
    b = world.h["admin_b"]
    assert (await c.get(f"{API}/containers/{box['id']}", headers=b)).status_code == 404
    assert (await c.post(f"{API}/containers/{box['id']}/allocate-costs", headers=b)).status_code == 404
    assert (await c.delete(f"{API}/containers/{box['id']}", headers=b)).status_code == 404
    assert (await c.get(f"{API}/containers/", headers=b)).json()["total"] == 0
    # ...and A's container is untouched
    assert (await c.get(f"{API}/containers/{box['id']}", headers=world.h["admin_a"])).status_code == 200


async def test_a_clerk_only_sees_their_own_containers(world):
    c = world.client
    mine = await make_container(c, world.h["clerk_a"], "mine")
    theirs = await make_container(c, world.h["clerk2_a"], "theirs")
    assert (await c.get(f"{API}/containers/{theirs['id']}", headers=world.h["clerk_a"])).status_code == 404
    ids = [x["id"] for x in (await c.get(f"{API}/containers/", headers=world.h["clerk_a"])).json()["items"]]
    assert ids == [mine["id"]]
    # a manager sees the whole organisation
    seen = (await c.get(f"{API}/containers/", headers=world.h["manager_a"])).json()["total"]
    assert seen == 2


async def test_only_managers_can_delete(world):
    c = world.client
    box = await make_container(c, world.h["clerk_a"])
    assert (await c.delete(f"{API}/containers/{box['id']}", headers=world.h["clerk_a"])).status_code == 403
    assert (await c.delete(f"{API}/containers/{box['id']}", headers=world.h["manager_a"])).status_code == 200
    assert (await c.get(f"{API}/containers/{box['id']}", headers=world.h["admin_a"])).status_code == 404


async def test_same_idempotency_key_creates_only_one_container(world):
    c = world.client
    key = str(uuid.uuid4())
    headers = {**world.h["admin_a"], "Idempotency-Key": key}
    body = {"name": "Once", "container_type": "40ft"}
    first = await c.post(f"{API}/containers/", headers=headers, json=body)
    again = await c.post(f"{API}/containers/", headers=headers, json=body)
    assert first.status_code == again.status_code == 201
    assert again.json()["id"] == first.json()["id"]
    assert again.headers.get("idempotent-replayed") == "true"
    clash = await c.post(f"{API}/containers/", headers=headers, json={**body, "name": "Different"})
    assert clash.status_code == 422
    assert (await c.get(f"{API}/containers/", headers=world.h["admin_a"])).json()["total"] == 1


async def test_cost_allocation_adds_up_exactly(world):
    c, h = world.client, world.h["admin_a"]
    box = await make_container(c, h)
    for i in range(3):
        await add_item(c, h, box["id"], f"item{i}")
    await add_expense(c, h, box["id"], "100.00")
    r = await c.post(f"{API}/containers/{box['id']}/allocate-costs", headers=h,
                     params={"allocation_method": "weight_based"})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert sum(Decimal(str(i["allocated_cost"])) for i in items) == Decimal("100")   # no cent lost to rounding
    assert sum(Decimal(str(i["landed_cost"])) for i in items) == Decimal("130")      # 3 x 10.00 + 100.00


async def test_viewers_cannot_allocate_costs(world):
    box = await make_container(world.client, world.h["admin_a"])
    r = await world.client.post(f"{API}/containers/{box['id']}/allocate-costs", headers=world.h["viewer_a"])
    assert r.status_code == 403


async def test_allocating_by_weight_needs_every_weight_but_value_allocation_does_not(world):
    from app.tests.api_helpers import add_expense
    c, h = world.client, world.h["admin_a"]
    box = await make_container(c, h)
    await add_item(c, h, box["id"], "known", price="10.00", weight="2.000")
    await add_item(c, h, box["id"], "unknown", price="30.00", weight=None)
    await add_expense(c, h, box["id"], amount="100.00")
    r = await c.post(f"{API}/containers/{box['id']}/allocate-costs", headers=h, params={"allocation_method": "weight_based"})
    assert r.status_code == 422 and "no weight" in r.text
    r = await c.post(f"{API}/containers/{box['id']}/allocate-costs", headers=h, params={"allocation_method": "value_based"})
    assert r.status_code == 200, r.text