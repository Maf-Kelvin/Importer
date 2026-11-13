# app/tests/test_pricing.py
"""HTTP-level tests for pricing: permissions, tenant isolation and the minimum-margin floor.
Only USD and no market scraping, so nothing here needs the network."""
import pytest

from app.tests.api_helpers import API, add_expense, add_item, make_container

pytestmark = pytest.mark.asyncio


async def _priced_item(world):
    """Three $10 items sharing a $100 expense -> the first item's landed cost is 43.3334."""
    c, h = world.client, world.h["admin_a"]
    box = await make_container(c, h)
    items = [await add_item(c, h, box["id"], f"item{i}") for i in range(3)]
    await add_expense(c, h, box["id"], "100.00")
    r = await c.post(f"{API}/containers/{box['id']}/allocate-costs", headers=h, params={"allocation_method": "weight_based"})
    assert r.status_code == 200, r.text
    return items[0]


async def test_a_clerk_gets_an_explainable_recommendation(world):
    item = await _priced_item(world)
    r = await world.client.post(f"{API}/pricing/generate/{item['id']}", headers=world.h["admin_a"],
                                json={"include_market_pricing": False})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["price_low"] is not None and body["price_high"] is not None
    assert body["confidence"] is not None and len(body["explanation"]) >= 1


async def test_recommendation_never_goes_below_the_minimum_margin(world):
    item = await _priced_item(world)
    r = await world.client.post(f"{API}/pricing/generate/{item['id']}", headers=world.h["admin_a"],
                                json={"include_market_pricing": False})
    assert r.json()["recommended_price"] >= 45.5      # landed cost 43.3334 x 1.05


async def test_viewers_cannot_generate_or_record_prices_or_scrape(world):
    item = await _priced_item(world)
    v, c = world.h["viewer_a"], world.client
    assert (await c.post(f"{API}/pricing/generate/{item['id']}", headers=v, json={"include_market_pricing": False})).status_code == 403
    assert (await c.post(f"{API}/pricing/refresh-market/{item['id']}", headers=v)).status_code == 403
    assert (await c.post(f"{API}/pricing/record", headers=v, json={
        "item_id": item["id"], "method": "market_based", "price": 99, "currency": "USD"})).status_code == 403


async def test_other_organisations_cannot_touch_an_items_pricing(world):
    item = await _priced_item(world)
    b, c = world.h["admin_b"], world.client
    assert (await c.post(f"{API}/pricing/generate/{item['id']}", headers=b, json={"include_market_pricing": False})).status_code == 404
    assert (await c.post(f"{API}/pricing/refresh-market/{item['id']}", headers=b)).status_code == 404
    assert (await c.post(f"{API}/pricing/record", headers=b, json={
        "item_id": item["id"], "method": "market_based", "price": 99, "currency": "USD"})).status_code == 404
    assert (await c.get(f"{API}/pricing/item/{item['id']}", headers=b)).status_code == 404


async def test_price_history_is_readable_by_the_owner(world):
    item = await _priced_item(world)
    await world.client.post(f"{API}/pricing/generate/{item['id']}", headers=world.h["admin_a"], json={"include_market_pricing": False})
    for role in ("admin_a", "viewer_a"):
        assert (await world.client.get(f"{API}/pricing/item/{item['id']}", headers=world.h[role])).status_code == 200


async def test_pricing_accuracy_report_is_for_managers_and_up(world):
    c = world.client
    assert (await c.get(f"{API}/pricing/accuracy", headers=world.h["viewer_a"])).status_code == 403
    assert (await c.get(f"{API}/pricing/accuracy", headers=world.h["clerk_a"])).status_code == 403
    assert (await c.get(f"{API}/pricing/accuracy", headers=world.h["manager_a"])).status_code == 200