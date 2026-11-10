# scripts/smoke_test.py
"""
End-to-end smoke test against a RUNNING stack.

    python scripts/smoke_test.py --base-url http://localhost:8000

Needs a platform administrator (created by scripts/init_db.py). Credentials come
from FIRST_SUPERUSER_USERNAME / FIRST_SUPERUSER_PASSWORD or --username/--password.

It creates two throw-away organisations and checks the behaviours that matter:
tenant isolation, role permissions, idempotency, exact cost allocation and the
audit trail. It only uses USD so it does not depend on the exchange-rate API.
Note: when Nginx is in front it rate-limits login (5/min); this test signs in several times,
so run it against the API directly (port 8000) or wait a minute between runs.
"""
import argparse
import os
import sys
import uuid
from decimal import Decimal

import httpx

PASSWORD = "Sm0ke-Test-Passw0rd!"
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("SMOKE_BASE_URL", "http://localhost:8000"))
    ap.add_argument("--username", default=os.getenv("FIRST_SUPERUSER_USERNAME"))
    ap.add_argument("--password", default=os.getenv("FIRST_SUPERUSER_PASSWORD"))
    args = ap.parse_args()
    if not (args.username and args.password):
        print("Provide the platform administrator via --username/--password or FIRST_SUPERUSER_* variables.")
        return 2

    api = args.base_url.rstrip("/") + "/api/v1"
    c = httpx.Client(timeout=30)
    run = uuid.uuid4().hex[:8]

    def login(username: str, password: str) -> dict:
        r = c.post(f"{api}/auth/login", data={"username": username, "password": password})
        r.raise_for_status()
        return {"Authorization": "Bearer " + r.json()["access_token"]}

    print("\n== Platform ==")
    check("liveness /health", c.get(args.base_url + "/health").status_code == 200)
    ready = c.get(args.base_url + "/ready")
    check("readiness /ready (database, schema, Redis)", ready.status_code == 200, ready.text[:200])
    check("self-registration is disabled", c.post(f"{api}/auth/register", json={
        "email": f"x{run}@example.com", "username": f"x{run}", "first_name": "X", "last_name": "Y",
        "password": PASSWORD, "role": "viewer"}).status_code == 403)

    print("\n== Onboarding two organisations ==")
    su = login(args.username, args.password)
    orgs = {}
    for tag in ("a", "b"):
        r = c.post(f"{api}/organizations/", headers=su, json={
            "name": f"Smoke {tag.upper()} {run}", "slug": f"smoke-{tag}-{run}",
            "admin_email": f"admin-{tag}-{run}@example.com", "admin_username": f"admin_{tag}_{run}",
            "admin_password": PASSWORD, "admin_first_name": "Admin", "admin_last_name": tag.upper()})
        check(f"create organisation {tag.upper()}", r.status_code == 201, r.text[:200])
        if r.status_code != 201:
            return summary()
        orgs[tag] = r.json()
    dup = c.post(f"{api}/organizations/", headers=su, json={
        "name": "Dup", "slug": f"smoke-a-{run}", "admin_email": f"dup{run}@example.com",
        "admin_username": f"dup_{run}", "admin_password": PASSWORD,
        "admin_first_name": "D", "admin_last_name": "D"})
    check("duplicate organisation slug rejected (409)", dup.status_code == 409)

    admin_a = login(f"admin_a_{run}", PASSWORD)
    admin_b = login(f"admin_b_{run}", PASSWORD)
    check("non-platform admin cannot create organisations",
          c.post(f"{api}/organizations/", headers=admin_a, json={
              "name": "Nope", "slug": f"nope-{run}", "admin_email": f"n{run}@example.com",
              "admin_username": f"n_{run}", "admin_password": PASSWORD,
              "admin_first_name": "N", "admin_last_name": "N"}).status_code == 403)

    print("\n== Roles ==")
    r = c.post(f"{api}/users/", headers=admin_a, json={
        "email": f"viewer-{run}@example.com", "username": f"viewer_{run}", "first_name": "V",
        "last_name": "W", "password": PASSWORD, "role": "viewer"})
    check("admin A creates a viewer", r.status_code == 201, r.text[:200])
    viewer_id = r.json().get("id")
    viewer = login(f"viewer_{run}", PASSWORD)
    check("viewer cannot create a container", c.post(f"{api}/containers/", headers=viewer, json={
        "name": "nope", "container_type": "20ft"}).status_code == 403)
    check("viewer can list containers", c.get(f"{api}/containers/", headers=viewer).status_code == 200)
    check("a weak password is refused when creating a user (422)", c.post(f"{api}/users/", headers=admin_a, json={
        "email": f"weak-{run}@example.com", "username": f"weak_{run}", "first_name": "W", "last_name": "P",
        "password": "short", "role": "viewer"}).status_code == 422)
    check("an admin cannot demote their own account (409)",
          c.put(f"{api}/users/{orgs['a']['admin_user_id']}", headers=admin_a, json={"role": "viewer"}).status_code == 409)
    check("an admin cannot deactivate their own account (400)",
          c.delete(f"{api}/users/{orgs['a']['admin_user_id']}", headers=admin_a).status_code == 400)
    check("renaming a user to an existing username is a conflict, not a crash (409)",
          c.put(f"{api}/users/{viewer_id}", headers=admin_a, json={"username": f"admin_a_{run}"}).status_code == 409)
    c.put(f"{api}/users/me", headers=viewer, json={"role": "admin", "first_name": "Vee"})
    me = c.get(f"{api}/users/me", headers=viewer).json()
    check("a user cannot promote themselves through their own profile", me["role"] == "viewer" and me["first_name"] == "Vee", str(me))

    print("\n== Containers, items, expenses (organisation A) ==")
    key = str(uuid.uuid4())
    body = {"name": f"Smoke container {run}", "container_type": "40ft", "allocation_method": "weight_based"}
    r1 = c.post(f"{api}/containers/", headers={**admin_a, "Idempotency-Key": key}, json=body)
    check("create container", r1.status_code == 201, r1.text[:200])
    cid = r1.json()["id"]
    r2 = c.post(f"{api}/containers/", headers={**admin_a, "Idempotency-Key": key}, json=body)
    check("same Idempotency-Key replays the same response",
          r2.status_code == 201 and r2.json()["id"] == cid and r2.headers.get("idempotent-replayed") == "true")
    r3 = c.post(f"{api}/containers/", headers={**admin_a, "Idempotency-Key": key},
                json={**body, "name": "different"})
    check("same key with a different body is rejected (422)", r3.status_code == 422)
    listing = c.get(f"{api}/containers/", headers=admin_a).json()
    check("duplicate request created only one container",
          sum(1 for x in listing["items"] if x["id"] == cid) == 1 and listing["total"] == 1)

    item_ids = []
    for i in range(3):
        r = c.post(f"{api}/items/", headers=admin_a, json={
            "container_id": cid, "name": f"item{i}", "category": "other", "condition": "new",
            "purchase_price": "10.00", "purchase_currency": "USD", "weight": "1.000"})
        check(f"add item {i}", r.status_code == 201, r.text[:200])
        item_ids.append(r.json().get("id"))
    r = c.post(f"{api}/expenses/", headers=admin_a, json={
        "container_id": cid, "expense_type": "shipping_fee", "amount": "100.00", "currency": "USD"})
    check("add expense", r.status_code == 201, r.text[:200])

    r = c.post(f"{api}/containers/{cid}/allocate-costs", headers=admin_a,
               params={"allocation_method": "weight_based"})
    check("allocate costs", r.status_code == 200, r.text[:200])
    if r.status_code == 200:
        data = r.json()
        shares = [Decimal(str(i["allocated_cost"])) for i in data["items"]]
        landed = [Decimal(str(i["landed_cost"])) for i in data["items"]]
        check("100.00 split over 3 equal items adds up exactly", sum(shares) == Decimal("100"), str(shares))
        check("landed cost = price + share (total 130)", sum(landed) == Decimal("130"), str(landed))

    print("\n== Tenant isolation (organisation B must see nothing of A) ==")
    check("B cannot read A's container", c.get(f"{api}/containers/{cid}", headers=admin_b).status_code == 404)
    check("B cannot allocate A's container",
          c.post(f"{api}/containers/{cid}/allocate-costs", headers=admin_b).status_code == 404)
    check("B cannot delete A's container", c.delete(f"{api}/containers/{cid}", headers=admin_b).status_code == 404)
    users_b = c.get(f"{api}/users/", headers=admin_b).json()
    names_b = {u["username"] for u in users_b["items"]}
    check("B's user list contains only B's users", names_b == {f"admin_b_{run}"}, str(names_b))
    check("B cannot read A's user", c.get(f"{api}/users/{viewer_id}", headers=admin_b).status_code == 404)
    check("B cannot promote A's user", c.put(f"{api}/users/{viewer_id}", headers=admin_b,
                                             json={"role": "admin"}).status_code == 404)
    check("B cannot deactivate A's user", c.delete(f"{api}/users/{viewer_id}", headers=admin_b).status_code == 404)
    check("B's container list is empty", c.get(f"{api}/containers/", headers=admin_b).json()["total"] == 0)
    check("B cannot see A's audit trail",
          all(e["entity_id"] != cid for e in c.get(f"{api}/audit-logs/", headers=admin_b).json()["items"]
              if e.get("entity_type") == "Container"))

    print("\n== Audit trail (organisation A) ==")
    logs = c.get(f"{api}/audit-logs/", headers=admin_a, params={"limit": 100}).json()["items"]
    actions = {e["action"] for e in logs}
    for expected in ("user.created", "container.created", "item.created", "expense.created", "costs.allocated"):
        check(f"audit has '{expected}'", expected in actions)
    check("non-admin cannot read the audit trail",
          c.get(f"{api}/audit-logs/", headers=viewer).status_code == 403)


    print("\n== Round-two audit: tracking, pricing, customers, files ==")
    check("viewer cannot trigger a tracking update",
          c.post(f"{api}/tracking/{cid}/update", headers=viewer).status_code == 403)
    check("B cannot trigger tracking for A's container",
          c.post(f"{api}/tracking/{cid}/update", headers=admin_b).status_code == 404)
    check("B cannot read A's tracking history",
          c.get(f"{api}/tracking/{cid}/history", headers=admin_b).json() == [])
    iid = item_ids[0]
    check("B cannot generate pricing for A's item",
          c.post(f"{api}/pricing/generate/{iid}", headers=admin_b, json={}).status_code == 404)
    check("B cannot queue market scraping for A's item",
          c.post(f"{api}/pricing/refresh-market/{iid}", headers=admin_b).status_code == 404)
    check("B cannot attach a price record to A's item",
          c.post(f"{api}/pricing/record", headers=admin_b, json={
              "item_id": iid, "method": "market_based", "price": 99, "currency": "USD"}).status_code == 404)
    check("B cannot read A's price history", c.get(f"{api}/pricing/item/{iid}", headers=admin_b).status_code == 404)
    check("viewer cannot generate pricing (it saves a price on the item)",
          c.post(f"{api}/pricing/generate/{iid}", headers=viewer, json={"include_market_pricing": False}).status_code == 403)
    check("viewer cannot start market scraping",
          c.post(f"{api}/pricing/refresh-market/{iid}", headers=viewer).status_code == 403)
    pr = c.post(f"{api}/pricing/generate/{iid}", headers=admin_a, json={"include_market_pricing": False})
    check("A gets an explainable price recommendation", pr.status_code == 200, pr.text[:200])
    if pr.status_code == 200:
        body = pr.json()
        check("recommendation has a band, confidence and reasons",
              body["price_low"] is not None and body["price_high"] is not None
              and body["confidence"] is not None and len(body["explanation"]) >= 1)
        check("recommendation is never below the minimum margin (landed 43.3334 x 1.05)",
              body["recommended_price"] >= 45.5)

    cust = c.post(f"{api}/customers/", headers=admin_a, json={"name": "Ada Buyer", "email": f"ada{run}@example.com"})
    check("A creates a customer", cust.status_code == 201, cust.text[:200])
    cust_id = cust.json().get("id")
    check("B cannot read A's customer", c.get(f"{api}/customers/{cust_id}", headers=admin_b).status_code == 404)
    check("B's customer list is empty", c.get(f"{api}/customers/", headers=admin_b).json()["total"] == 0)
    check("B cannot delete A's customer", c.delete(f"{api}/customers/{cust_id}", headers=admin_b).status_code == 404)

    # B builds an item and tries to sell it to A's customer
    cb = c.post(f"{api}/containers/", headers=admin_b, json={"name": "B box", "container_type": "20ft"}).json()
    ib = c.post(f"{api}/items/", headers=admin_b, json={
        "container_id": cb["id"], "name": "b item", "category": "other", "condition": "new",
        "purchase_price": "5.00", "purchase_currency": "USD", "weight": "1.000"}).json()
    r = c.post(f"{api}/items/{ib['id']}/mark-sold", headers=admin_b,
               json={"selling_price": "9.00", "customer_id": cust_id})
    check("a sale cannot reference another organisation's customer (422)", r.status_code == 422, r.text[:200])

    print("\n== Report accuracy (profit = revenue - cost of SOLD items) ==")
    r = c.post(f"{api}/items/{iid}/mark-sold", headers=admin_a,
               json={"selling_price": "60.00", "customer_id": cust_id})
    check("A sells item 0 for 60.00", r.status_code == 200, r.text[:200])
    r = c.post(f"{api}/expenses/", headers=admin_a, json={
        "container_id": cid, "expense_type": "clearing_fee", "amount": "20.00", "currency": "USD"})
    check("add a second expense after allocation", r.status_code == 201, r.text[:200])
    rows = c.get(f"{api}/reports/profit/containers", headers=admin_a).json()
    mine = next((x for x in rows if x["container_id"] == cid), None)
    check("container report found", mine is not None)
    if mine:
        d = lambda k: Decimal(str(mine[k]))
        check("total expenses is 120 (old join fan-out would show 360)", d("total_expenses") == Decimal("120"), str(mine))
        check("3 items counted once each", mine["total_items"] == 3 and mine["items_sold"] == 1)
        check("revenue 60, cost of goods sold 43.3334", d("total_revenue") == Decimal("60") and d("cost_of_goods_sold") == Decimal("43.3334"), str(mine))
        check("profit = 60 - 43.3334 = 16.6666 (unsold stock is not a loss)", d("total_profit") == Decimal("16.6666"), str(mine))
        check("inventory value = 86.6666", d("inventory_value") == Decimal("86.6666"))
        check("20.00 of expenses flagged as not yet allocated", d("unallocated_expenses") == Decimal("20"), str(mine))
    dash = c.get(f"{api}/reports/dashboard", headers=admin_a).json()
    check("dashboard profit matches", Decimal(str(dash["total_profit"])) == Decimal("16.6666"), str(dash))

    print("\n== Files ==")
    import base64
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
    up = c.post(f"{api}/files/upload", headers=admin_a, files={"file": ("photo.png", png, "image/png")})
    check("A uploads an image", up.status_code == 201, up.text[:200])
    if up.status_code == 201:
        key = up.json()["file_key"]
        check("file key is tenant-scoped", key.startswith(f"{orgs['a']['id']}/"))
        check("A can download it", c.get(f"{api}/files/{key}", headers=admin_a).status_code == 200)
        check("B cannot download A's file", c.get(f"{api}/files/{key}", headers=admin_b).status_code == 404)
        check("B cannot delete A's file", c.delete(f"{api}/files/{key}", headers=admin_b).status_code == 404)
        check("a path-traversal key is rejected", c.delete(f"{api}/files/..%2f..%2fapp%2fmain.py", headers=admin_a).status_code == 404)
        check("A can delete it", c.delete(f"{api}/files/{key}", headers=admin_a).status_code == 200)
    check("a file that is not an allowed type is rejected",
          c.post(f"{api}/files/upload", headers=admin_a, files={"file": ("x.png", b"not an image at all", "image/png")}).status_code == 400)

    print("\n== Web session (httpOnly refresh cookie) ==")
    web = httpx.Client(timeout=30)
    r = web.post(f"{api}/auth/login", data={"username": f"admin_a_{run}", "password": PASSWORD},
                 headers={"X-Auth-Mode": "cookie"})
    check("web login succeeds", r.status_code == 200, r.text[:200])
    check("web login keeps the refresh token OUT of the JSON body", r.json().get("refresh_token") is None)
    cookie = r.headers.get("set-cookie", "").lower()
    check("refresh cookie is httpOnly, SameSite=Strict and path-scoped",
          "httponly" in cookie and "samesite=strict" in cookie and "path=/api/v1/auth" in cookie, cookie[:200])
    r2 = web.post(f"{api}/auth/refresh", headers={"X-Auth-Mode": "cookie"})
    check("refresh works from the cookie alone", r2.status_code == 200 and bool(r2.json().get("access_token")), r2.text[:200])
    check("a cookie without the X-Auth-Mode header is not accepted (CSRF guard)",
          web.post(f"{api}/auth/refresh").status_code == 401)
    check("logout clears the session", web.post(f"{api}/auth/logout", headers={
        "X-Auth-Mode": "cookie", "Authorization": "Bearer " + r2.json()["access_token"]}).status_code == 200)

    print("\n== Sign-out works even with an expired access token ==")
    web2 = httpx.Client(timeout=30)
    web2.post(f"{api}/auth/login", data={"username": f"admin_a_{run}", "password": PASSWORD}, headers={"X-Auth-Mode": "cookie"})
    cookie_value = web2.cookies.get("refresh_token")
    check("logout needs no access token (it revokes the session cookie)",
          web2.post(f"{api}/auth/logout", headers={"X-Auth-Mode": "cookie"}).status_code == 200)
    check("the refresh token is dead after logout",
          httpx.Client(timeout=30, cookies={"refresh_token": cookie_value}).post(
              f"{api}/auth/refresh", headers={"X-Auth-Mode": "cookie"}).status_code == 401)

    print("\n== Refresh-token rotation is atomic ==")
    from concurrent.futures import ThreadPoolExecutor
    web3 = httpx.Client(timeout=30)
    web3.post(f"{api}/auth/login", data={"username": f"admin_a_{run}", "password": PASSWORD}, headers={"X-Auth-Mode": "cookie"})
    shared = web3.cookies.get("refresh_token")

    def refresh_once(_):
        return httpx.Client(timeout=30, cookies={"refresh_token": shared}).post(
            f"{api}/auth/refresh", headers={"X-Auth-Mode": "cookie"}).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(refresh_once, range(8)))
    check("8 simultaneous refreshes with the same token: exactly ONE succeeds", codes.count(200) == 1 and codes.count(401) == 7, str(codes))

    print("\n== Clerks only see their own containers' numbers ==")
    r = c.post(f"{api}/users/", headers=admin_a, json={
        "email": f"clerk-{run}@example.com", "username": f"clerk_{run}", "first_name": "C",
        "last_name": "K", "password": PASSWORD, "role": "clerk"})
    check("admin A creates a clerk", r.status_code == 201, r.text[:200])
    clerk = login(f"clerk_{run}", PASSWORD)
    check("clerk cannot open another user's container", c.get(f"{api}/containers/{cid}", headers=clerk).status_code == 404)
    kc = c.post(f"{api}/containers/", headers=clerk, json={"name": "Clerk box", "container_type": "20ft"}).json()
    c.post(f"{api}/items/", headers=clerk, json={
        "container_id": kc["id"], "name": "clerk item", "category": "other", "condition": "new",
        "purchase_price": "7.00", "purchase_currency": "USD", "weight": "1.000"})
    dash_c = c.get(f"{api}/reports/dashboard", headers=clerk).json()
    check("clerk dashboard counts only their own container", dash_c["active_containers"] == 1, str(dash_c))
    check("clerk dashboard counts only their own items", dash_c["total_items"] == 1, str(dash_c))
    check("clerk dashboard shows none of the organisation's revenue", Decimal(str(dash_c["total_revenue"])) == 0, str(dash_c))
    check("clerk gets no organisation-wide stock alerts", dash_c["low_stock_alerts"] == 0)
    check("organisation-wide demand analytics are refused to clerks (403)",
          c.get(f"{api}/reports/demand", headers=clerk).status_code == 403)
    check("admin can read demand analytics", c.get(f"{api}/reports/demand", headers=admin_a).status_code == 200)
    check("clerk's profit-by-category report excludes other people's items",
          sum(x["total_items"] for x in c.get(f"{api}/reports/profit/categories", headers=clerk).json()) == 1)

    print("\n== Soft-deleted items must not reappear ==")
    tmp = c.post(f"{api}/items/", headers=admin_a, json={
        "container_id": cid, "name": "temp", "category": "other", "condition": "new",
        "purchase_price": "1.00", "purchase_currency": "USD", "weight": "1.000"}).json()
    c.delete(f"{api}/items/{tmp['id']}", headers=admin_a)
    detail = c.get(f"{api}/containers/{cid}", headers=admin_a).json()
    check("deleted item is absent from the container detail", all(i["id"] != tmp["id"] for i in detail["items"]))

    logs = c.get(f"{api}/audit-logs/", headers=admin_a, params={"limit": 100}).json()["items"]
    actions = {e["action"] for e in logs}
    for expected in ("customer.created", "item.sold", "file.deleted"):
        check(f"audit has '{expected}'", expected in actions)

    return summary()


def summary() -> int:
    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
