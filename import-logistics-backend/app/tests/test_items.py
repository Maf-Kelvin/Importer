# app/tests/test_items.py
"""HTTP-level tests for items and sales: permissions, tenant isolation, sold-once guarantee."""
import asyncio

import pytest
from sqlalchemy import func, select

from app.tests.api_helpers import API, NO_TOKEN, add_item, make_container

pytestmark = pytest.mark.asyncio

# A second sale is refused with 400 ("not found or already sold"); two sales racing at the same
# instant give the loser 409. Both are clean client errors; what matters is that it is never a 500.
REFUSED = (400, 409, 422)


async def _sales_for(world, item_id: int) -> int:
    from app.models.commerce import Sale
    async with world.sessions() as s:
        return (await s.execute(select(func.count()).select_from(Sale).where(Sale.item_id == item_id))).scalar_one()


async def _customer(world, headers, name="Ada Buyer") -> dict:
    r = await world.client.post(f"{API}/customers/", headers=headers, json={"name": name, "email": f"{name[:3].lower()}@example.com"})
    assert r.status_code == 201, r.text
    return r.json()


async def test_add_and_read_an_item(world):
    c, h = world.client, world.h["admin_a"]
    box = await make_container(c, h)
    item = await add_item(c, h, box["id"], "lamp", price="12.50")
    got = await c.get(f"{API}/items/{item['id']}", headers=h)
    assert got.status_code == 200 and got.json()["name"] == "lamp"
    assert (await c.get(f"{API}/items/999999", headers=h)).status_code == 404


async def test_viewers_cannot_add_items_and_anonymous_users_cannot_either(world):
    c = world.client
    box = await make_container(c, world.h["admin_a"])
    body = {"container_id": box["id"], "name": "x", "category": "other", "condition": "new",
            "purchase_price": "1.00", "purchase_currency": "USD", "weight": "1.000"}
    assert (await c.post(f"{API}/items/", headers=world.h["viewer_a"], json=body)).status_code == 403
    assert (await c.post(f"{API}/items/", json=body)).status_code in NO_TOKEN


async def test_an_item_cannot_be_added_to_another_organisations_container(world):
    c = world.client
    box = await make_container(c, world.h["admin_a"])
    r = await c.post(f"{API}/items/", headers=world.h["admin_b"], json={
        "container_id": box["id"], "name": "sneaky", "category": "other", "condition": "new",
        "purchase_price": "1.00", "purchase_currency": "USD", "weight": "1.000"})
    assert r.status_code in (400, 404), r.text


async def test_other_organisations_cannot_read_or_change_an_item(world):
    c = world.client
    box = await make_container(c, world.h["admin_a"])
    item = await add_item(c, world.h["admin_a"], box["id"])
    b = world.h["admin_b"]
    assert (await c.get(f"{API}/items/{item['id']}", headers=b)).status_code == 404
    assert (await c.put(f"{API}/items/{item['id']}", headers=b, json={"name": "hijacked"})).status_code == 404
    assert (await c.delete(f"{API}/items/{item['id']}", headers=b)).status_code == 404
    assert (await c.get(f"{API}/items/{item['id']}", headers=world.h["admin_a"])).json()["name"] != "hijacked"


async def test_deleted_items_disappear_from_the_container(world):
    c, h = world.client, world.h["admin_a"]
    box = await make_container(c, h)
    keep = await add_item(c, h, box["id"], "keep")
    gone = await add_item(c, h, box["id"], "gone")
    assert (await c.delete(f"{API}/items/{gone['id']}", headers=h)).status_code == 200
    ids = [i["id"] for i in (await c.get(f"{API}/containers/{box['id']}", headers=h)).json()["items"]]
    assert ids == [keep["id"]]


async def test_mark_sold_records_one_sale(world):
    c, h = world.client, world.h["admin_a"]
    item = await add_item(c, h, (await make_container(c, h))["id"])
    r = await c.post(f"{API}/items/{item['id']}/mark-sold", headers=h, json={"selling_price": "60.00"})
    assert r.status_code == 200, r.text
    assert await _sales_for(world, item["id"]) == 1


async def test_viewers_cannot_mark_items_sold(world):
    c = world.client
    item = await add_item(c, world.h["admin_a"], (await make_container(c, world.h["admin_a"]))["id"])
    r = await c.post(f"{API}/items/{item['id']}/mark-sold", headers=world.h["viewer_a"], json={"selling_price": "5.00"})
    assert r.status_code == 403


async def test_an_item_cannot_be_sold_twice(world):
    c, h = world.client, world.h["admin_a"]
    item = await add_item(c, h, (await make_container(c, h))["id"])
    first = await c.post(f"{API}/items/{item['id']}/mark-sold", headers=h, json={"selling_price": "60.00"})
    second = await c.post(f"{API}/items/{item['id']}/mark-sold", headers=h, json={"selling_price": "70.00"})
    assert first.status_code == 200 and second.status_code in REFUSED
    assert await _sales_for(world, item["id"]) == 1


async def test_two_simultaneous_sales_record_exactly_one(world):
    """Two cashiers press 'sold' at the same moment: one wins, the other gets a clean 4xx (not a 500)."""
    c, h = world.client, world.h["admin_a"]
    item = await add_item(c, h, (await make_container(c, h))["id"])
    url = f"{API}/items/{item['id']}/mark-sold"
    results = await asyncio.gather(*[
        world.make_client(f"203.0.113.{i}").post(url, headers=h, json={"selling_price": "60.00"}) for i in range(1, 5)
    ])
    codes = sorted(r.status_code for r in results)
    assert codes.count(200) == 1, codes
    assert all(code in REFUSED for code in codes if code != 200), codes
    assert await _sales_for(world, item["id"]) == 1


async def test_a_sale_cannot_name_another_organisations_customer(world):
    c = world.client
    a_customer = await _customer(world, world.h["admin_a"])
    item_b = await add_item(c, world.h["admin_b"], (await make_container(c, world.h["admin_b"]))["id"])
    r = await c.post(f"{API}/items/{item_b['id']}/mark-sold", headers=world.h["admin_b"],
                     json={"selling_price": "9.00", "customer_id": a_customer["id"]})
    assert r.status_code == 422, r.text
    assert await _sales_for(world, item_b["id"]) == 0


async def test_weight_is_optional_when_adding_an_item(world):
    c, h = world.client, world.h["admin_a"]
    box = await make_container(c, h)
    item = await add_item(c, h, box["id"], "mystery box", weight=None)
    assert item["weight"] is None
    got = await c.get(f"{API}/items/{item['id']}", headers=h)
    assert got.status_code == 200 and got.json()["weight"] is None
    # a weight can be added later
    r = await c.put(f"{API}/items/{item['id']}", headers=h, json={"weight": "2.500"})
    assert r.status_code == 200 and float(r.json()["weight"]) == 2.5


async def test_a_zero_weight_is_still_refused(world):
    c, h = world.client, world.h["admin_a"]
    box = await make_container(c, h)
    r = await c.post(f"{API}/items/", headers=h, json={
        "container_id": box["id"], "name": "x", "category": "other", "condition": "new",
        "purchase_price": "5.00", "purchase_currency": "USD", "weight": "0"})
    assert r.status_code == 422