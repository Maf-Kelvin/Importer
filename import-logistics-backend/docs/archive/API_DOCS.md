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