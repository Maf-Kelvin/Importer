# API Reference

Base URL: `https://yourdomain.com/api/v1`

All endpoints require `Authorization: Bearer <access_token>` unless marked **Public**.

Idempotent mutation endpoints accept an optional `Idempotency-Key: <uuid>` header to safely retry requests from mobile clients.

---

## Authentication

### POST /auth/login — Public
Authenticate and receive access + refresh tokens.

**Request** (form-data)
```
username=admin
password=yourpassword
```

**Response 200**
```json
{
  "access_token":  "eyJ...",
  "refresh_token": "eyJ...",
  "token_type":    "bearer",
  "expires_in":    86400
}
```

**Errors**
- `401` — Incorrect credentials or account locked
- `403` — Account inactive

---

### POST /auth/refresh — Public
Exchange a refresh token for a new access + refresh token pair. Old refresh token is blacklisted (rotation).

**Request body**
```json
{ "refresh_token": "eyJ..." }
```

**Response 200** — same shape as `/auth/login`

**Errors**
- `401` — Token invalid, expired, or revoked

---

### POST /auth/logout
Revoke both the access token and refresh token.

**Request body**
```json
{ "refresh_token": "eyJ..." }
```

**Response 200**
```json
{ "message": "Logged out successfully" }
```

---

### POST /auth/register — Public
Create a new account. Role cannot be `admin` — use `POST /users/` for admin creation.

**Request body**
```json
{
  "email":      "user@example.com",
  "username":   "johndoe",
  "first_name": "John",
  "last_name":  "Doe",
  "password":   "strongpassword",
  "role":       "viewer"
}
```

**Response 201** — UserInDB

**Errors**
- `409` — Email or username already exists

---

## Users

### GET /users/ — Admin only
List all users with pagination.

**Query params**
```
page=1&limit=20
```

**Response 200** — PagedResponse[UserInDB]

---

### GET /users/me
Get current authenticated user profile.

**Response 200** — UserInDB

---

### PUT /users/me
Update own profile. Cannot change own role.

**Request body** (all fields optional)
```json
{
  "first_name": "John",
  "last_name":  "Smith",
  "password":   "newpassword"
}
```

---

### POST /users/ — Admin only
Create a user with any role.

**Request body** — UserAdminCreate (same as register + any role)

---

### PUT /users/{user_id} — Admin only
Update any user including role and is_active.

---

### DELETE /users/{user_id} — Admin only
Deactivates the user (soft disable — does not delete).

---

## Containers

### POST /containers/ — Clerk+
Create a new container.

**Request body**
```json
{
  "name":                 "CONT-2024-001",
  "container_type":       "40ft",
  "msc_container_number": "MSCU123456789",
  "allocation_method":    "weight_based",
  "notes":                "Electronics batch"
}
```

**Response 201** — ContainerInDB

**Headers**
```
Idempotency-Key: <uuid>
```

---

### GET /containers/
List containers. Clerks see only their own.

**Query params**
```
page=1&limit=20&owner_id=5&container_type=40ft&is_shipped=false
```

**Response 200** — PagedResponse[ContainerInDB]

---

### GET /containers/{container_id}
Get container with all items and expenses.

**Response 200** — ContainerWithItems

---

### PUT /containers/{container_id} — Clerk+
Update container name, MSC number, allocation method, or notes.

---

### DELETE /containers/{container_id} — Manager+
Soft-delete a container.

---

### POST /containers/{container_id}/seal — Clerk+
Seal container. No more items can be added after sealing.

---

### POST /containers/{container_id}/allocate-costs — Clerk+
Distribute container expenses across all items.

**Query params**
```
allocation_method=weight_based  (or value_based)
```

**Response 200**
```json
{
  "method":         "weight_based",
  "total_expenses": 3200.00,
  "total_weight":   450.5,
  "items": [
    {
      "item_id":        1,
      "weight_ratio":   0.056,
      "allocated_cost": 179.2,
      "landed_cost":    979.2
    }
  ]
}
```

---

## Items

### POST /items/ — Clerk+
Add an item to a container. Container must not be sealed.

**Request body**
```json
{
  "container_id":      1,
  "name":              "Samsung 55\" TV",
  "category":          "electronics",
  "condition":         "new",
  "purchase_price":    800.00,
  "purchase_currency": "USD",
  "purchase_date":     "2024-01-15",
  "weight":            25.5,
  "volume":            0.3
}
```

**Response 201** — ItemInDB

---

### GET /items/
List items with filters and optional search.

**Query params**
```
page=1&limit=20&container_id=1&category=electronics&condition=new&sold=false&search=samsung
```

---

### GET /items/{item_id}
Get item with full pricing history.

**Response 200** — ItemWithPricing

---

### PUT /items/{item_id} — Clerk+
Update item details.

---

### DELETE /items/{item_id} — Clerk+
Soft-delete an item.

---

### POST /items/{item_id}/mark-sold — Clerk+
Mark an item as sold. Creates a Sale record.

**Request body**
```json
{
  "selling_price": 1200.00,
  "sold_date":     "2024-03-01",
  "customer_id":   5,
  "notes":         "Sold at market"
}
```

**Response 200** — ItemInDB

**Errors**
- `400` — Item already sold or not found

---

## Expenses

### POST /expenses/ — Clerk+
Add an expense to a container.

**Request body**
```json
{
  "container_id": 1,
  "expense_type": "shipping_fee",
  "amount":       2000.00,
  "currency":     "USD",
  "description":  "MSC shipping Lagos to Prague"
}
```

**Response 201** — ExpenseInDB

---

### GET /expenses/container/{container_id}
List all expenses for a container.

---

### PUT /expenses/{expense_id} — Clerk+
Update expense amount, currency, or description. USD amount auto-recalculated.

---

### DELETE /expenses/{expense_id} — Clerk+
Delete an expense.

---

## Pricing

### POST /pricing/generate/{item_id}
Generate pricing recommendations. Optionally triggers async market scrape.

**Request body**
```json
{
  "include_cost_based":     true,
  "include_market_pricing": true,
  "include_last_sold":      true,
  "profit_margin":          0.25,
  "sources":                ["jiji", "ebay"]
}
```

**Response 200**
```json
{
  "item_id":           1,
  "landed_cost":       979.20,
  "cost_based_price":  1224.00,
  "market_prices": [
    {
      "source":     "ebay",
      "price":      1150.00,
      "currency":   "USD",
      "confidence": 0.8,
      "found_at":   "2024-03-01T10:00:00Z"
    }
  ],
  "last_sold_price":   1100.00,
  "recommended_price": 1158.00,
  "profit_margin":     0.25,
  "generated_at":      "2024-03-01T10:00:00Z"
}
```

---

### POST /pricing/refresh-market/{item_id}
Enqueue a fresh market price scrape. Returns immediately.

---

### POST /pricing/record — Clerk+
Manually create a price record.

---

### GET /pricing/item/{item_id}
Get full price history for an item.

---

## Tracking

### POST /tracking/{container_id}/update
Enqueue an async tracking update via Celery.

---

### GET /tracking/{container_id}/history
Get full tracking history (newest first).

**Response 200** — List[TrackingRecordInDB]

---

### GET /tracking/{container_id}/status
Get current tracking status.

**Response 200**
```json
{
  "status":            "in_transit",
  "location":          "Atlantic Ocean",
  "vessel_name":       "MSC VESSEL 001",
  "voyage_number":     "V1001",
  "estimated_arrival": "2024-04-15T10:00:00Z",
  "last_updated":      "2024-03-01T08:00:00Z"
}
```

---

### POST /tracking/{container_id}/notifications — Clerk+
Update notification settings for a container.

**Request body**
```json
{
  "enable_notifications":  true,
  "notification_interval": 3,
  "email_notifications":   true,
  "webhook_url":           "https://yourapp.com/webhook"
}
```

---

## Reports

### GET /reports/dashboard
Dashboard summary metrics. Redis-cached for 5 minutes.

**Response 200**
```json
{
  "active_containers":  12,
  "total_items":        340,
  "items_sold":         210,
  "total_revenue":      185000.00,
  "total_profit":       42000.00,
  "avg_profit_margin":  0.294,
  "pending_shipments":  3,
  "low_stock_alerts":   2,
  "generated_at":       "2024-03-01T10:00:00Z"
}
```

---

### GET /reports/profit/items
Per-item profit report.

**Query params**
```
container_id=1&category=electronics&sold_only=true&start_date=2024-01-01&end_date=2024-03-31
```

---

### GET /reports/profit/containers — Manager+
Per-container profit report. Single aggregation query — no N+1.

**Query params**
```
owner_id=5
```

---

### GET /reports/profit/categories
Per-category profit report. Powered by SQL GROUP BY.

---

### GET /reports/demand
Demand analytics per category. Updated every 6 hours by Celery.

---

## Files

### POST /files/upload — Clerk+
Upload a file (item photo, document, invoice).

**Request** — multipart/form-data with `file` field

**Allowed MIME types:** `image/jpeg`, `image/png`, `image/webp`, `application/pdf`

**Max size:** 10 MB (configurable via `MAX_UPLOAD_SIZE`)

**Response 201**
```json
{
  "file_key":  "42/a3f9b2c1d4e5.jpg",
  "file_url":  "https://bucket.s3.amazonaws.com/42/a3f9b2c1d4e5.jpg",
  "file_size": 204800,
  "mime_type": "image/jpeg"
}
```

**Errors**
- `400` — File too large or MIME type not allowed

---

### DELETE /files/{file_key} — Clerk+
Delete an uploaded file from storage.

---

## Health

### GET /health — Public
Liveness probe. Always returns 200 if the process is running.

```json
{ "status": "ok", "service": "Import Profit & Logistics Intelligence System" }
```

---

### GET /ready — Public
Readiness probe. Checks database, Redis, and Celery workers.

**Response 200 (healthy)**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis":    "ok",
    "celery":   "ok"
  }
}
```

**Response 503 (degraded)**
```json
{
  "status": "degraded",
  "checks": {
    "database": "ok",
    "redis":    "error: Connection refused",
    "celery":   "no workers"
  }
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `POST /auth/login` | 5 requests / minute per IP |
| `GET/POST /tracking/*` | 20 requests / minute per IP |
| All other endpoints | 100 requests / minute per IP |

Rate limit errors return `429 Too Many Requests`.

---

## Pagination

All list endpoints use standardised pagination.

**Request**
```
GET /items/?page=2&limit=20
```

**Response envelope**
```json
{
  "items":    [...],
  "total":    142,
  "page":     2,
  "limit":    20,
  "pages":    8,
  "has_next": true,
  "has_prev": true
}
```

---

## Error Responses

All errors follow a consistent shape:

```json
{
  "detail": "Container not found"
}
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request — validation error or business rule violation |
| `401` | Unauthenticated — missing or invalid token |
| `403` | Forbidden — insufficient role |
| `404` | Resource not found |
| `409` | Conflict — duplicate resource |
| `422` | Unprocessable entity — schema validation failed |
| `429` | Rate limit exceeded |
| `500` | Internal server error |



















# API Reference

Base URL (local): `http://localhost:8000` - all business endpoints live under **`/api/v1`**.
Interactive docs (Swagger UI) at `/docs` are available when `ENVIRONMENT` is not `production`.
The table of endpoints below (53 endpoints) was generated from the router code, so it matches what is deployed.

## 1. Conventions

| Topic | Rule |
|-------|------|
| Format | JSON in and out (`Content-Type: application/json`), except login (form) and file upload (multipart) |
| Auth | `Authorization: Bearer <access_token>` |
| Money | Sent and returned as JSON numbers. Max 4 decimal places for amounts, 8 for FX rates, 3 for weight/volume. More decimals = `422` |
| Currencies | `USD`, `EUR`, `CZK`, `NGN` (ISO code, 3 letters). Amounts are converted to USD when saved |
| Dates | ISO 8601 (`2026-10-23`); timestamps are UTC |
| Pagination | `?page=1&limit=20` (limit max 100). List responses: `{items, total, page, limit, pages, has_next, ...}` |
| Idempotency | Send `Idempotency-Key: <8-128 chars>` on POST/PUT/PATCH (see section 5) |
| Soft delete | Containers and items are soft-deleted and disappear from lists |
| Rate limits | Login 5/min, tracking 20/min, other 100/min (per client). Exceeding returns `429` |

## 2. Authentication

1. **Login** - `POST /api/v1/auth/login`, **form-encoded** (`application/x-www-form-urlencoded`) with fields `username` and `password` (OAuth2 password form).

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin" -d "password=YOUR_PASSWORD"
```
```json
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer", "expires_in": 86400 }
```
2. **Call the API** with `Authorization: Bearer <access_token>`.
3. **Refresh** - `POST /api/v1/auth/refresh`. Each refresh token works **exactly once**: the exchange is atomic, so if the same token is sent twice, even at the same instant, one request succeeds and the others get `401`.
   - *API clients:* JSON body `{"refresh_token": "..."}` (`Content-Type: application/json`).
   - *Web app:* send the header `X-Auth-Mode: cookie` and no body; the refresh token travels in an httpOnly, SameSite=Strict cookie (path `/api/v1/auth`) that JavaScript cannot read. The same request with only the cookie and no header is rejected (CSRF guard).
4. **Logout** - `POST /api/v1/auth/logout` is **public**: it revokes whichever tokens you present and, in web mode, clears the cookie. It does not need a valid access token, so a user whose access token has expired can still sign out. Send the refresh token in the JSON body (API clients) or the cookie plus `X-Auth-Mode: cookie` (web); send `Authorization: Bearer ...` too if you have it so the access token is revoked as well.

| Endpoint | Request content type | Credential |
|----------|----------------------|------------|
| `POST /auth/login` | `application/x-www-form-urlencoded` | username + password |
| `POST /auth/refresh` | JSON body (API clients) or none (web mode) | refresh token (body or cookie) |
| `POST /auth/logout` | JSON body (API clients) or none (web mode) | none required; revokes what you present |
| everything else | JSON (`application/json`), multipart for file upload | `Authorization: Bearer` |

**Where the frontend runs:** the bundled setup is same-origin (Vite proxy in development, Nginx in production), so CORS is not involved. If you host the frontend on a different origin, list that exact origin in `BACKEND_CORS_ORIGINS` (never a wildcard: requests carry credentials) and keep both on the same *site* (for example `app.example.com` and `api.example.com`), because the refresh cookie is `SameSite=Strict`.

Access tokens last 30 minutes and refresh tokens 30 days by default (`ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_MINUTES`). Tokens carry the user id and a fingerprint of the password, so changing a password ends every existing session.
Accounts lock after repeated failed logins (`MAX_LOGIN_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES`).
Self-registration is **off by default**; an admin creates users with `POST /api/v1/users/`.

### Roles

| Role | Can |
|------|-----|
| `viewer` | Read containers, items, expenses, pricing, tracking, reports (organisation-wide) |
| `clerk` | Viewer + create/update containers, items, expenses, files, price records, tracking notification settings. Clerks only see their **own** containers, and every total built from them: the dashboard and the item and category reports count only a clerk's own containers; organisation-wide stock alerts show 0 and `GET /reports/demand` returns `403` for clerks |
| `manager` | Clerk + delete containers, per-container profit report, sees all containers in the tenant |
| `admin` | Manager + user management and the audit trail (own organisation only) |
| platform administrator (`is_superuser`) | Creates organisations and their first admin (`POST /organizations/`); not a role inside a tenant |

Every record belongs to a tenant (organisation). You can only ever see your own tenant's data, including users: an admin lists, reads, edits and deactivates only users of their own organisation (other organisations' users return `404`).

## 3. Endpoints

### Auth

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| POST | `/api/v1/auth/login` | Public | 200 | `Token` | Login and receive access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Public | 200 | `Token` | Exchange a refresh token for a new access token |
| POST | `/api/v1/auth/logout` | Public | 200 | `dict` | Sign out: revoke the presented tokens and clear the session cookie |
| POST | `/api/v1/auth/register` | Public | 201 | `UserInDB` | Register a new user (admin-gated in production) |

### Users

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| GET | `/api/v1/users` | Admin | 200 | `PagedResponse[UserInDB]` | List all users (admin only) |
| GET | `/api/v1/users/me` | Any signed-in user | 200 | `UserInDB` | Get current user profile |
| PUT | `/api/v1/users/me` | Any signed-in user | 200 | `UserInDB` | Update own profile (cannot change own role) |
| POST | `/api/v1/users` | Admin | 201 | `UserInDB` | Create user (admin only — any role allowed) |
| GET | `/api/v1/users/{user_id}` | Admin | 200 | `UserInDB` | Get user by ID (admin only) |
| PUT | `/api/v1/users/{user_id}` | Admin | 200 | `UserInDB` | Update any user (admin only) |
| DELETE | `/api/v1/users/{user_id}` | Admin | 200 |  | Deactivate user (admin only — soft disable, not delete) |

### Organizations

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| POST | `/api/v1/organizations` | Platform administrator | 201 | `OrganizationCreated` | Create an organisation and its first admin (platform administrator only) |
| GET | `/api/v1/organizations/me` | Any signed-in user | 200 | `OrganizationOut` | Your organisation |

### Customers

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| POST | `/api/v1/customers` | Clerk or higher | 201 | `CustomerInDB` | Create a customer |
| GET | `/api/v1/customers` | Any signed-in user | 200 | `PagedResponse[CustomerInDB]` | List customers |
| GET | `/api/v1/customers/{customer_id}` | Any signed-in user | 200 | `CustomerInDB` | Get a customer |
| PUT | `/api/v1/customers/{customer_id}` | Clerk or higher | 200 | `CustomerInDB` | Update a customer |
| DELETE | `/api/v1/customers/{customer_id}` | Manager or admin | 204 |  | Delete a customer (manager+; sales history is kept) |

### Containers

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| POST | `/api/v1/containers` | Clerk or higher | 201 | `ContainerInDB` | Create a new container |
| GET | `/api/v1/containers` | Any signed-in user | 200 | `PagedResponse[ContainerInDB]` | List containers (role-filtered) |
| GET | `/api/v1/containers/{container_id}` | Any signed-in user | 200 | `ContainerWithItems` | Get container with all items and expenses |
| PUT | `/api/v1/containers/{container_id}` | Clerk or higher | 200 | `ContainerInDB` | Update container |
| DELETE | `/api/v1/containers/{container_id}` | Manager or admin | 200 |  | Soft-delete container (manager+ only) |
| POST | `/api/v1/containers/{container_id}/seal` | Clerk or higher | 200 |  | Seal container — no more items can be added |
| POST | `/api/v1/containers/{container_id}/allocate-costs` | Clerk or higher | 200 |  | Allocate container expenses to items |

### Items

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| POST | `/api/v1/items` | Clerk or higher | 201 | `ItemInDB` | Add item to a container |
| GET | `/api/v1/items` | Any signed-in user | 200 | `PagedResponse[ItemInDB]` | List items with filters |
| GET | `/api/v1/items/{item_id}` | Any signed-in user | 200 | `ItemWithPricing` | Get item with full pricing history |
| PUT | `/api/v1/items/{item_id}` | Clerk or higher | 200 | `ItemInDB` | Update item details |
| DELETE | `/api/v1/items/{item_id}` | Clerk or higher | 200 |  | Soft-delete item |
| POST | `/api/v1/items/{item_id}/mark-sold` | Clerk or higher | 200 | `ItemInDB` | Mark item as sold — creates a Sale record |

### Expenses

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| POST | `/api/v1/expenses` | Clerk or higher | 201 | `ExpenseInDB` | Add expense to a container |
| GET | `/api/v1/expenses/container/{container_id}` | Any signed-in user | 200 | `list[ExpenseInDB]` | List all expenses for a container |
| PUT | `/api/v1/expenses/{expense_id}` | Clerk or higher | 200 | `ExpenseInDB` | Update an expense |
| DELETE | `/api/v1/expenses/{expense_id}` | Clerk or higher | 200 |  | Delete an expense |

### Pricing

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| POST | `/api/v1/pricing/generate/{item_id}` | Clerk or higher | 200 | `PricingResponse` | Generate pricing recommendation for an item |
| POST | `/api/v1/pricing/refresh-market/{item_id}` | Clerk or higher | 200 |  | Trigger market price refresh for an item (async) |
| POST | `/api/v1/pricing/record` | Clerk or higher | 201 | `PriceRecordInDB` | Manually create a price record |
| GET | `/api/v1/pricing/item/{item_id}` | Any signed-in user | 200 | `list[PriceRecordInDB]` | Get full price history for an item |
| GET | `/api/v1/pricing/accuracy` | Manager or admin | 200 | `PricingAccuracy` | How accurate recommendations were vs actual sale prices (manager+) |

### Tracking

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| POST | `/api/v1/tracking/{container_id}/update` | Clerk or higher | 200 |  | Manually trigger a tracking update (async) |
| GET | `/api/v1/tracking/{container_id}/history` | Any signed-in user | 200 | `list[TrackingRecordInDB]` | Get full tracking history for a container |
| GET | `/api/v1/tracking/{container_id}/status` | Any signed-in user | 200 | `TrackingStatusResponse` | Get current tracking status |
| POST | `/api/v1/tracking/{container_id}/notifications` | Clerk or higher | 200 |  | Update tracking notification settings for a container |

### Reports

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| GET | `/api/v1/reports/dashboard` | Any signed-in user | 200 | `DashboardSummary` | Dashboard summary metrics (Redis-cached 5 min) |
| GET | `/api/v1/reports/profit/items` | Any signed-in user | 200 | `list[ProfitReportItem]` | Per-item profit report |
| GET | `/api/v1/reports/profit/containers` | Manager or admin | 200 | `list[ContainerReport]` | Per-container profit report (manager+ only) |
| GET | `/api/v1/reports/profit/categories` | Any signed-in user | 200 | `list[CategoryReport]` | Per-category profit report - SQL GROUP BY |
| GET | `/api/v1/reports/demand` | Any signed-in user | 200 | `list[DemandSnapshot]` | Demand analytics per category |

### Files

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| POST | `/api/v1/files/upload` | Clerk or higher | 201 |  | Upload a file (item photo, document, invoice) |
| GET | `/api/v1/files/{file_key:path}` | Any signed-in user | 200 |  | Download a file (your organisation's files only) |
| DELETE | `/api/v1/files/{file_key:path}` | Clerk or higher | 200 |  | Delete an uploaded file (your own, or any in your organisation if manager/admin) |

### Audit log

| Method | Path | Access | Status | Response | Purpose |
|---|---|---|---|---|---|
| GET | `/api/v1/audit-logs` | Admin | 200 | `PagedResponse[AuditLogOut]` | Audit trail for your organisation (admin only, newest first) |

### Health and operations (no `/api/v1` prefix, no auth)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness: process is up |
| GET | `/ready` | Readiness: database + migrated schema + state Redis (503 if not ready); reports cache and Celery |
| GET | `/metrics` | Prometheus metrics |

## 4. Common request examples

**Create a container**
```bash
curl -X POST http://localhost:8000/api/v1/containers/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"name":"Lagos Jan shipment","container_type":"40ft",
       "msc_container_number":"MSCU1234567","allocation_method":"weight_based"}'
```
`container_type`: `20ft` | `40ft`. `allocation_method`: `weight_based` | `value_based`.

**Add an item** (`category`: electronics, vehicles, engines, appliances, food_items, laptops, other; `condition`: new, tokunbo, used)
```json
POST /api/v1/items/
{ "container_id": 1, "name": "iPhone 13", "category": "electronics", "condition": "used",
  "purchase_price": 450.00, "purchase_currency": "EUR", "weight": 0.5 }
```

**Add an expense** (`expense_type`: loading_fee, shipping_fee, clearing_fee, offloading_fee, warehouse_fee, security_fee, extra_fee)
```json
POST /api/v1/expenses/
{ "container_id": 1, "expense_type": "shipping_fee", "amount": 3200.00, "currency": "USD" }
```
The USD amount and FX rate are calculated server-side. If no exchange rate can be obtained in production, the API answers `503` with `Retry-After`.

**Allocate costs** - `POST /api/v1/containers/{id}/allocate-costs?allocation_method=weight_based`
```json
{ "method": "weight_based", "total_expenses": 4200.0, "allocated_total": 4200.0, "basis_total": 12.5,
  "items": [ { "item_id": 7, "item_name": "iPhone 13", "ratio": 0.04, "allocated_cost": 168.0, "landed_cost": 590.0 } ] }
```
The per-item shares always add up to `total_expenses` exactly. `422` if the container has no items or the method is unknown; `404` if it is not yours.

**Mark an item sold** - `POST /api/v1/items/{id}/mark-sold` with `{"selling_price": 700.00, "sold_date": "2026-10-23"}`.

**Upload a file** - `POST /api/v1/files/upload` (multipart field `file`). Allowed: JPEG, PNG, WebP, PDF, max 10 MB; the type is verified from the file content, not the name.
Returns `{file_key, file_url, file_size, mime_type}`. The key looks like `<organisation>/<user>/<random>.png`.
Download with `GET /api/v1/files/{file_key}` (needs your token; other organisations' files return 404, so image widgets must send the `Authorization` header or use a signed URL). Delete with `DELETE /api/v1/files/{file_key}` (your own files; managers and admins can delete any file in their organisation).

## 5. Idempotent writes

Send a unique `Idempotency-Key` with every create (POST) so a retry never creates a duplicate.

| Situation | Response |
|-----------|----------|
| First request | Processed normally; a 2xx result is remembered for 24 h |
| Same key + same request | Same response again, with header `Idempotent-Replayed: true` |
| Same key + different request | `422` |
| Same key while the first is still running | `409` + `Retry-After: 1` |
| First request failed (non-2xx) | Key is released; safe to retry |
| Key not 8-128 chars of letters/digits/`_-.:` | `400` |

Keys are private to your user; two users can reuse the same key value.

## 6. Errors

```json
{ "detail": "Container not found" }
```
Validation errors (`422`) return `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`.

| Code | Meaning |
|------|---------|
| 400 | Malformed request / bad idempotency key |
| 401 | Missing, invalid, expired or revoked token |
| 403 | Role too low, or self-registration disabled |
| 404 | Not found (also returned for another tenant's record) |
| 409 | Duplicate (e.g. user exists) or idempotent request still running |
| 422 | Validation failed or business rule blocked it (e.g. nothing to allocate) |
| 429 | Rate limit exceeded |
| 503 | Dependency unavailable (exchange rates, idempotency store) - retry later |

## 6a. Managing users

* Passwords must be **12 to 128 characters** (new users and password changes).
* `PUT /users/me` edits your own profile (name, email, username, password). It cannot change your role or active flag; its request type no longer offers those fields.
* An admin **cannot change their own role or deactivate their own account** (`409` / `400`), so an organisation can never be left without an administrator. Another admin can.
* Changing an email or username to one that is already taken returns `409`, not a server error.
* `DELETE /users/{id}` **deactivates** the account (history is kept); re-activate it with `PUT /users/{id}` and `{"is_active": true}`.

## 7. Audit trail

Every create, update and delete of containers, expenses and items, every cost allocation, every sale and every user change is recorded
(who, what, when, from which IP, and the before/after values for changes). Admins read it with `GET /api/v1/audit-logs/`
(filters: `action` prefix such as `expense.`, `entity_type`, `user_id`). The audit row is saved in the same database transaction as the change, so one cannot exist without the other.
Actions: `container.created|updated|sealed|deleted`, `expense.created|updated|deleted`, `item.created|updated|deleted|sold`, `costs.allocated`, `user.created|updated|deactivated`, `organization.created`.
Passwords and tokens are never stored in the trail.

## 8. Pricing recommendations

`POST /api/v1/pricing/generate/{item_id}` returns an explainable recommendation, not just a number:

```json
{ "item_id": 7, "landed_cost": 43.33, "cost_based_price": 52.0,
  "recommended_price": 58.4, "price_low": 52.5, "price_high": 66.0,
  "confidence": 0.62, "expected_margin": 0.348, "comparables_used": 7,
  "warnings": [], "explanation": ["Market median 61.0 from 7 comparable(s) (effective sample 4.2, price spread 18%).",
                                   "Blended 62% market / 38% cost-plus (52.00)."] }
```
See `PRICING.md` for how it works. `GET /api/v1/pricing/accuracy` (manager+) reports how close past recommendations were to the real sale prices.

## 9. Not exposed yet

The database has tables for suppliers, orders, payments, shipments, ports, customs clearance, documents and warehouses, but **no API endpoints use them yet** (see `DATABASE.md`).