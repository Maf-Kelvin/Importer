# System Architecture

## Overview

The Import Profit & Logistics Intelligence System follows a layered clean architecture with clear separation between API routing, business logic, data access, and background processing. It is designed as a multi-tenant SaaS platform with horizontal scaling in mind.

---

## Full System Architecture

```
                        ┌─────────────────────────────┐
                        │   Clients                   │
                        │   Flutter Mobile / Desktop  │
                        │   Flutter Web               │
                        └────────────┬────────────────┘
                                     │ HTTPS
                        ┌────────────▼────────────────┐
                        │   Nginx Reverse Proxy        │
                        │   SSL termination            │
                        │   Gzip compression           │
                        │   Rate limiting zones        │
                        │   Security headers           │
                        └────────────┬────────────────┘
                                     │ HTTP/2
                        ┌────────────▼────────────────┐
                        │   FastAPI Application        │
                        │   Gunicorn + UvicornWorker   │
                        │   (2 × CPU + 1 workers)      │
                        └──┬──────────┬───────────────┘
                           │          │
          ┌────────────────▼──┐   ┌───▼────────────────┐
          │   PgBouncer        │   │   Redis 7           │
          │   Connection pool  │   │   Cache             │
          │   transaction mode │   │   Celery broker     │
          └────────┬───────────┘   │   Token blacklist   │
                   │               │   Idempotency keys  │
          ┌────────▼───────────┐   │   Rate limit state  │
          │   PostgreSQL 16     │   │   Distributed locks │
          │   Primary (writes)  │   └───────┬────────────┘
          │   35+ tables        │           │
          └────────────────────┘   ┌────────▼────────────┐
                                   │   Celery Workers     │
                                   │   worker-tracking    │
                                   │   worker-pricing     │
                                   │   worker-fx-notify   │
                                   │   celery-beat        │
                                   └──────────────────────┘

External Services
├── MSC Container Tracking API
├── ExchangeRate API (FX rates)
├── Jiji / eBay / Mobile.de / AutoScout24 / Bazos.cz (scraping)
├── SMTP / SendGrid / Mailgun / SES (email)
└── AWS S3 / Cloudflare R2 (file storage)

Monitoring Stack
├── Prometheus (metrics scraping)
├── Grafana (dashboards)
├── Sentry (error tracking)
├── Flower (Celery task monitoring)
└── OpenTelemetry (distributed tracing)
```

---

## Backend Internal Architecture

The backend follows a strict layered architecture. No layer reaches past its immediate neighbour.

```
HTTP Request
     │
     ▼
┌──────────────────────────────────┐
│  Middleware Layer                 │
│  CORS → Logging → Metrics        │
│  → Idempotency                   │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Router Layer  (app/routers/)    │
│  Request validation              │
│  Rate limiting                   │
│  Authentication (deps.py)        │
│  Role enforcement                │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Service Layer  (app/services/)  │
│  Business logic                  │
│  Ownership checks                │
│  Tenant isolation                │
│  Transaction management          │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Model Layer  (app/models/)      │
│  SQLAlchemy ORM                  │
│  Async queries                   │
│  Relationship loading            │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Database  (PostgreSQL)          │
│  via PgBouncer                   │
└──────────────────────────────────┘
```

---

## Worker Architecture

Celery workers are separated by concern into dedicated queues. This prevents a flood of scraping jobs from starving time-sensitive tracking updates.

```
Celery Beat (scheduler)
     │
     ├── fx_queue          (every 1h)  ──▶  worker-fx-notify
     ├── tracking_queue    (every 1h)  ──▶  worker-tracking
     ├── notification_queue (every 1h) ──▶  worker-fx-notify
     └── pricing_queue     (every 6h)  ──▶  worker-pricing

On-demand tasks (triggered by API):
     ├── scraping_queue   ──▶  worker-pricing
     ├── tracking_queue   ──▶  worker-tracking
     └── notification_queue ──▶ worker-fx-notify

Queue assignment:
┌─────────────────────┬────────────────────────────────────┐
│ Queue               │ Tasks                              │
├─────────────────────┼────────────────────────────────────┤
│ tracking_queue      │ update_container_tracking          │
│                     │ update_all_tracking                │
├─────────────────────┼────────────────────────────────────┤
│ scraping_queue      │ fetch_market_prices                │
├─────────────────────┼────────────────────────────────────┤
│ pricing_queue       │ update_item_pricing                │
│                     │ refresh_demand_analytics           │
├─────────────────────┼────────────────────────────────────┤
│ fx_queue            │ update_fx_rates                    │
├─────────────────────┼────────────────────────────────────┤
│ notification_queue  │ send_tracking_notifications        │
│                     │ send_custom_notification           │
│                     │ notify_low_stock                   │
└─────────────────────┴────────────────────────────────────┘

Reliability features:
- task_acks_late=True          Task only acknowledged after completion
- task_reject_on_worker_lost   Re-queued if worker dies mid-task
- max_retries=3                Automatic retry with backoff
- Distributed Redis locks      Prevent duplicate periodic tasks
```

---

## Authentication & Security Architecture

```
Login Request
     │
     ▼
Account lockout check (Redis)
     │
     ▼
Password verification (bcrypt)
     │
     ▼
Issue access token (15min–24h)  +  refresh token (30 days)
     │                                    │
     ▼                                    ▼
Stored client-side                Stored client-side
Used for API calls                Used to rotate access token
     │
     ▼
Every API request:
  1. Extract Bearer token
  2. Check Redis blacklist (O(1) lookup)
  3. Decode + verify JWT signature
  4. Verify token type = "access"
  5. Load user from DB
  6. Check is_active
  7. Enforce role-based access

Logout:
  - Blacklist access token (TTL = remaining expiry)
  - Blacklist refresh token (TTL = remaining expiry)
  - Tokens expire naturally — no cleanup job needed

Token rotation:
  - Each /auth/refresh call issues new access + refresh tokens
  - Old refresh token is immediately blacklisted
```

---

## Multi-Tenancy Architecture

Every table in the database includes a `tenant_id` foreign key to `organizations`. Data isolation is enforced at the service layer on every query.

```
organizations (tenants)
     │
     ├── users          (tenant_id)
     ├── containers     (tenant_id)
     ├── items          (tenant_id)
     ├── expenses       (tenant_id)
     ├── price_records  (tenant_id)
     ├── tracking       (tenant_id)
     ├── warehouses     (tenant_id)
     ├── customers      (tenant_id)
     ├── orders         (tenant_id)
     ├── payments       (tenant_id)
     ├── sales          (tenant_id)
     ├── notifications  (tenant_id)
     ├── audit_logs     (tenant_id)
     └── demand_analytics (tenant_id)

Isolation rule:
  Every service method filters by current_user.tenant_id.
  A user from tenant A can never read or write tenant B's data.
```

---

## Data Flow: Container Import Lifecycle

```
1. Create Container
   POST /containers/
        │
        ▼
2. Add Items
   POST /items/  (×N)
        │
        ▼
3. Add Expenses
   POST /expenses/  (loading, shipping, clearing...)
        │
        ▼
4. Seal Container
   POST /containers/{id}/seal
        │
        ▼
5. Allocate Costs
   POST /containers/{id}/allocate-costs
        │  Each item.allocated_cost and item.landed_cost calculated
        ▼
6. Generate Pricing
   POST /pricing/generate/{item_id}
        │  cost_based_price = landed_cost × (1 + margin)
        │  market_prices = from scraper results
        │  recommended_price = weighted average
        ▼
7. Track Shipment
   Celery beat → update_all_tracking (every 1h)
        │  MSC API → TrackingRecord created
        │  Email notification → owner
        ▼
8. Mark Items Sold
   POST /items/{id}/mark-sold
        │  Item.sold = true
        │  Sale record created
        │  Profit calculated
        ▼
9. View Reports
   GET /reports/profit/containers
   GET /reports/profit/categories
   GET /reports/dashboard  (Redis-cached 5min)
```

---

## Caching Architecture

```
Redis Cache Layers:

┌─────────────────────────────────────────────┐
│ Key pattern              │ TTL   │ Invalidated by        │
├──────────────────────────┼───────┼───────────────────────┤
│ dashboard:{t}:{u}        │ 5 min │ Item sold / container │
│ fx_rate:{from}:{to}      │ 1 hr  │ fx_worker update      │
│ pricing:{item_id}        │ 30min │ New price record       │
│ idempotency:{u}:{key}    │ 24 hr │ Never (TTL only)       │
│ bl:{token}               │ Token │ Never (TTL only)       │
│                          │ TTL   │                       │
│ login_fail:{username}    │ 15min │ Successful login       │
│ lock:{name}              │ Task  │ Task completion        │
│                          │ TTL   │                       │
└─────────────────────────────────────────────┘
```

---

## File Storage Architecture

```
Upload request
     │
     ▼
MIME type validation (python-magic — reads bytes, not extension)
     │
     ▼
File size check (max 10 MB)
     │
     ▼
Generate safe key: {uploader_id}/{uuid}.{ext}
     │
     ▼
Storage backend (config-driven):
  ├── local  →  /app/uploads/{key}
  ├── s3     →  s3://{bucket}/{key}
  └── r2     →  r2://{bucket}/{key}  (Cloudflare R2, S3-compatible API)
```

---

## Deployment Architecture

```
Development:
  docker-compose.yml
  └── db + pgbouncer + redis + web(uvicorn reload)
      + worker-tracking + worker-pricing + worker-fx-notify
      + celery-beat + flower + prometheus + grafana

Production:
  docker-compose.prod.yml
  └── nginx (SSL, rate limiting)
      └── web × 2 (gunicorn + uvicornworker)
          ├── pgbouncer → db (no exposed port)
          ├── redis (password protected, no exposed port)
          ├── worker-tracking × 1 (concurrency=4)
          ├── worker-pricing × 1 (concurrency=2)
          ├── worker-fx-notify × 1 (concurrency=2)
          ├── celery-beat × 1
          ├── flower (basic auth, internal only)
          ├── prometheus (internal only)
          └── grafana (internal only)

Future scaling path:
  Kubernetes + Horizontal Pod Autoscaler
  ├── web deployment (scale by CPU/request rate)
  ├── worker deployments (scale by queue depth)
  └── Read replica for reporting queries
```