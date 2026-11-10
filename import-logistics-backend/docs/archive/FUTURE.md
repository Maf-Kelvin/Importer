# Future Roadmap

This document outlines the planned evolution of the Import Profit & Logistics Intelligence System across Phase 2, Phase 3, and beyond. Phase 1 (the current production rewrite) is complete and forms the stable foundation everything below builds on.

---

## Phase 1 — Complete ✅

**Status:** Production-ready

Everything in Phase 1 is built, documented, and deployable:

- Async FastAPI backend with 35+ table PostgreSQL schema
- Multi-tenant architecture with `tenant_id` isolation
- JWT access + refresh tokens with Redis blacklist and account lockout
- Full RBAC (Admin, Manager, Clerk, Viewer)
- Container, item, expense, pricing, tracking, warehouse, sales, commerce models
- Cost allocation (weight-based and value-based)
- Celery workers with 5 named queues, distributed locks, retry logic
- Market price scraping (httpx + Playwright)
- FX rate caching and history persistence
- Async email with provider abstraction (SMTP, SendGrid, Mailgun, SES)
- File uploads with MIME validation (local, S3, Cloudflare R2)
- Redis-backed cache service, idempotency middleware
- Structured JSON logging, Prometheus metrics, Sentry, OpenTelemetry
- Nginx reverse proxy with SSL, rate limiting, security headers
- Gunicorn + UvicornWorker production server
- PgBouncer connection pooling
- Docker Compose dev + prod stacks
- Alembic async migrations
- Full documentation (README, API_DOCS, ARCHITECTURE, DATABASE)

---

## Phase 2 — SaaS Hardening & Commerce

**Target:** 3–6 months after Phase 1

Phase 2 turns the platform into a billable multi-tenant SaaS product with a complete commerce layer, stronger data integrity, and read scalability.

---

### 2.1 Subscription Billing (Stripe)

**Why:** The `organizations.plan` and `organizations.max_containers` columns are already in the schema. Phase 2 wires them to real billing.

**What to build:**

`app/services/billing_service.py`
- Stripe Customer creation on organization signup
- Stripe Subscription creation, upgrade, and cancellation
- Webhook handler for `customer.subscription.updated`, `invoice.paid`, `invoice.payment_failed`
- Plan enforcement middleware — reject requests when limits exceeded

New tables:
```sql
CREATE TABLE subscriptions (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT REFERENCES organizations(id),
    stripe_customer_id      TEXT UNIQUE,
    stripe_subscription_id  TEXT UNIQUE,
    plan            TEXT,   -- starter / professional / enterprise
    status          TEXT,   -- active / past_due / canceled
    current_period_end TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE billing_events (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT REFERENCES organizations(id),
    event_type  TEXT,
    stripe_event_id TEXT UNIQUE,
    payload     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

New router: `app/routers/billing.py`
- `POST /billing/checkout` — create Stripe checkout session
- `POST /billing/portal` — customer portal for self-service
- `POST /billing/webhook` — Stripe webhook receiver (no auth, HMAC-verified)
- `GET /billing/plans` — list available plans

New env vars:
```
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_STARTER_PRICE_ID=
STRIPE_PRO_PRICE_ID=
STRIPE_ENTERPRISE_PRICE_ID=
```

**Dependencies:** `stripe==7.x`

---

### 2.2 Tenant Onboarding Flow

**Why:** Currently `tenant_id=1` is hardcoded in `/auth/register`. Phase 2 adds proper organisation creation.

**What to build:**

- `POST /organizations/` — create new organisation + first admin user in one transaction
- Organisation invitation system — admin generates invite token, new user registers via invite
- `POST /invites/` — generate invite link (admin only)
- `POST /invites/{token}/accept` — register via invite, auto-assigned to organisation
- Invite tokens stored in Redis with 48-hour TTL

New table:
```sql
CREATE TABLE invites (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT REFERENCES organizations(id),
    email       TEXT,
    role        TEXT,
    token       TEXT UNIQUE,
    accepted    BOOLEAN DEFAULT FALSE,
    expires_at  TIMESTAMPTZ,
    created_by  BIGINT REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2.3 Row-Level Security (PostgreSQL RLS)

**Why:** Service-layer `tenant_id` filtering is correct but is a soft boundary. RLS adds a hard database-level guarantee — even a buggy query cannot return another tenant's data.

**What to build:**

Alembic migration enabling RLS on critical tables:
```sql
ALTER TABLE containers ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON containers
    USING (tenant_id = current_setting('app.tenant_id')::bigint);
```

`database.py` — set `app.tenant_id` on each connection from the session:
```python
await session.execute(
    text("SET LOCAL app.tenant_id = :tid"),
    {"tid": current_user.tenant_id}
)
```

Tables to enable RLS on: `containers`, `items`, `expenses`, `price_records`, `tracking_records`, `orders`, `payments`, `sales`, `audit_logs`

**Note:** Requires PgBouncer in `session` mode (not `transaction` mode) or setting per-statement. Evaluate performance impact before enabling in production.

---

### 2.4 Read Replica for Reporting

**Why:** Heavy `GROUP BY` aggregation queries in `/reports/` compete with write traffic. A read replica separates concerns.

**What to build:**

Add `REPORTS_DATABASE_URL` to config — points to the PostgreSQL streaming replica.

`database.py` — second async engine:
```python
reports_engine = create_async_engine(settings.REPORTS_DATABASE_URL, ...)
ReportsSessionLocal = async_sessionmaker(bind=reports_engine, ...)
```

`app/routers/deps.py` — new dependency:
```python
async def get_reports_db() -> AsyncGenerator[AsyncSession, None]:
    async with ReportsSessionLocal() as session:
        yield session
```

Wire all `/reports/` endpoints to use `get_reports_db` instead of `get_db`.

New env var: `REPORTS_DATABASE_URL=postgresql+asyncpg://...` (replica connection string)

---

### 2.5 Elasticsearch Full-Text Search

**Why:** PostgreSQL `ilike` works for hundreds of items but degrades beyond tens of thousands. Elasticsearch enables instant search across item names, descriptions, and categories.

**What to build:**

`app/services/search_service.py`
- `index_item(item)` — index item on create/update
- `search_items(query, tenant_id, filters)` — search with tenant isolation
- `delete_item(item_id)` — remove on soft delete
- PostgreSQL fallback when `ELASTICSEARCH_URL` is not set

`app/workers/search_worker.py`
- `reindex_tenant(tenant_id)` — bulk reindex all items for a tenant
- `sync_item(item_id)` — sync single item to Elasticsearch

Item create/update/delete in `ContainerService` enqueues sync task.

New env var: `ELASTICSEARCH_URL=http://elasticsearch:9200`

Add to `docker-compose.yml`:
```yaml
elasticsearch:
  image: elasticsearch:8.12.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
  volumes:
    - es_data:/usr/share/elasticsearch/data
```

**Dependencies:** `elasticsearch==8.x`

---

### 2.6 Materialized Views for Analytics

**Why:** The `/reports/profit/containers` and `/reports/profit/categories` queries aggregate across large tables. Materialized views pre-compute results and make dashboards instant.

**What to build:**

Alembic migration creating materialized views:
```sql
CREATE MATERIALIZED VIEW mv_container_profit AS
SELECT
    c.id            AS container_id,
    c.tenant_id,
    c.name,
    SUM(e.amount_usd)                           AS total_expenses,
    COUNT(i.id)                                 AS total_items,
    COUNT(i.id) FILTER (WHERE i.sold)           AS items_sold,
    COALESCE(SUM(i.landed_cost), 0)             AS total_cost,
    COALESCE(SUM(i.selling_price) FILTER (WHERE i.sold), 0) AS total_revenue
FROM containers c
LEFT JOIN container_expenses e ON e.container_id = c.id
LEFT JOIN items i ON i.container_id = c.id AND i.deleted_at IS NULL
WHERE c.deleted_at IS NULL
GROUP BY c.id, c.tenant_id, c.name;

CREATE UNIQUE INDEX ON mv_container_profit (container_id);

CREATE MATERIALIZED VIEW mv_category_profit AS
SELECT
    i.tenant_id,
    i.category,
    COUNT(*)                                        AS total_items,
    COUNT(*) FILTER (WHERE i.sold)                  AS items_sold,
    COALESCE(SUM(i.landed_cost), 0)                 AS total_investment,
    COALESCE(SUM(i.selling_price) FILTER (WHERE i.sold), 0) AS total_revenue
FROM items i
JOIN containers c ON c.id = i.container_id
WHERE i.deleted_at IS NULL
GROUP BY i.tenant_id, i.category;
```

`app/workers/analytics_worker.py`
```python
@celery_app.task(queue="pricing_queue")
def refresh_materialized_views():
    # CONCURRENTLY — no table lock, safe for production
    db.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_container_profit")
    db.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_category_profit")
```

Beat schedule: every 15 minutes.

Reports router queries views instead of base tables.

---

### 2.7 WebSocket Live Updates

**Why:** Mobile clients currently poll for tracking and pricing changes. WebSockets push updates instantly.

**What to build:**

`app/routers/ws.py`
```python
@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: int):
    await manager.connect(websocket, tenant_id)
    try:
        while True:
            await websocket.receive_text()   # keep-alive ping
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)
```

`app/core/ws_manager.py` — connection manager with tenant-scoped broadcasting:
```python
class ConnectionManager:
    async def broadcast_to_tenant(self, tenant_id: int, event: dict): ...
```

Workers call `broadcast_to_tenant` after:
- Tracking status update
- Pricing recommendation generated
- Low stock alert triggered
- Order status changed

Redis Pub/Sub bridges multiple web worker processes:
- Worker publishes to Redis channel `ws:{tenant_id}`
- Each web worker subscribes and forwards to connected WebSockets

---

## Phase 3 — Intelligence & Scale

**Target:** 6–12 months after Phase 2

Phase 3 adds predictive intelligence, advanced analytics, and infrastructure for high-scale multi-region deployment.

---

### 3.1 AI Pricing Recommendations (ML Model)

**Why:** By Phase 3, the platform will have months of sales data, market prices, and demand scores. This is enough to train a useful pricing model.

**What to build:**

`app/services/ml_pricing_service.py`
- Feature engineering from `items`, `price_records`, `sales`, `demand_analytics`
- Model inference endpoint wrapping a trained Scikit-learn or XGBoost model
- A/B testing framework — compare ML recommendations vs rule-based

Training pipeline (`scripts/train_pricing_model.py`):
- Features: category, condition, weight, landed_cost, demand_score, avg_market_price, season
- Target: actual selling price (from `sales` table)
- Model: XGBoost regression with cross-validation
- Export: ONNX format for language-agnostic inference

New table:
```sql
CREATE TABLE ml_predictions (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT REFERENCES organizations(id),
    item_id         BIGINT REFERENCES items(id),
    model_version   TEXT,
    predicted_price NUMERIC,
    confidence      NUMERIC,
    features        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

`app/workers/ml_worker.py`
- `batch_predict_pricing(tenant_id)` — run inference on all unsold items nightly
- Model served from object storage (S3/R2), loaded at worker startup

**Dependencies:** `scikit-learn`, `xgboost`, `onnxruntime`

---

### 3.2 Demand Forecasting Engine

**Why:** Importers currently guess what to order. A forecasting engine tells them exactly what quantity to import and when.

**What to build:**

`app/services/forecast_service.py`
- Time-series forecasting using Prophet or statsmodels ARIMA
- Inputs: `sales` table grouped by category, date, tenant
- Outputs: projected units sold for next 30 / 60 / 90 days
- Reorder quantity suggestion = projected demand × safety factor

New table:
```sql
CREATE TABLE demand_forecasts (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT REFERENCES organizations(id),
    item_category   TEXT,
    forecast_date   DATE,
    horizon_days    INTEGER,
    predicted_units INTEGER,
    confidence_low  INTEGER,
    confidence_high INTEGER,
    model_version   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

New router endpoint: `GET /reports/forecast/{category}`

`app/workers/forecast_worker.py`
- `run_demand_forecast(tenant_id)` — weekly batch, all categories
- Results stored in `demand_forecasts`, surfaced in dashboard

**Dependencies:** `prophet` or `statsmodels`

---

### 3.3 Logistics Cost Simulator

**Why:** The most requested feature from importers. Simulate full landed cost before committing to a purchase order.

**What to build:**

`app/services/simulator_service.py`
- Input: supplier price, quantity, shipping estimate, duty rate, insurance, port fees
- Output: landed cost per unit, recommended sale price, projected margin, break-even price

New router: `POST /simulator/calculate`

```json
Request:
{
  "supplier_price":    20.00,
  "quantity":          500,
  "shipping_estimate": 3500.00,
  "duty_rate":         0.15,
  "insurance_rate":    0.005,
  "other_fees":        800.00,
  "target_margin":     0.35,
  "currency":          "USD"
}

Response:
{
  "total_landed_cost":       21200.00,
  "landed_cost_per_unit":    42.40,
  "recommended_sale_price":  57.24,
  "break_even_price":        42.40,
  "projected_profit":        7420.00,
  "projected_margin":        0.35,
  "roi":                     0.35
}
```

No database writes — pure calculation service. Results can optionally be saved as a `SimulationRecord` for history.

---

### 3.4 Freight Rate Comparison

**Why:** Importers use one carrier by default and overpay. Rate comparison could save 10–20% per shipment.

**What to build:**

`app/services/freight_service.py`
- Adapter pattern — one interface, multiple carrier implementations
- Initial carriers: MSC, Maersk (if API available), manual entry fallback
- Rate caching in Redis — freight rates change weekly, not hourly

New table:
```sql
CREATE TABLE freight_rates (
    id              BIGSERIAL PRIMARY KEY,
    carrier         TEXT,
    origin_port     TEXT,
    destination_port TEXT,
    container_type  TEXT,
    rate_usd        NUMERIC,
    valid_from      DATE,
    valid_to        DATE,
    source          TEXT,  -- api / manual
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

New router: `GET /freight/rates?origin=NGLAG&destination=CZPRG&container_type=40ft`

---

### 3.5 Supplier Performance Analytics

**Why:** Good suppliers make a business. Bad suppliers destroy it. This feature quantifies supplier reliability.

**What to build:**

New tables:
```sql
CREATE TABLE supplier_orders (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT REFERENCES organizations(id),
    supplier_id     BIGINT REFERENCES suppliers(id),
    container_id    BIGINT REFERENCES containers(id),
    order_date      DATE,
    promised_date   DATE,
    actual_date     DATE,
    total_value_usd NUMERIC,
    status          TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE supplier_ratings (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT REFERENCES organizations(id),
    supplier_id     BIGINT REFERENCES suppliers(id),
    on_time_rate    NUMERIC,   -- % orders delivered on time
    quality_score   NUMERIC,   -- 0-5
    avg_cost_index  NUMERIC,   -- relative to market average
    total_orders    INTEGER,
    calculated_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

`app/workers/analytics_worker.py` — weekly supplier score recalculation

New router: `GET /suppliers/{id}/performance`

---

### 3.6 Kubernetes Migration

**Why:** Docker Compose scales to a point. Kubernetes enables true horizontal autoscaling, rolling deployments, and multi-region.

**What to build:**

`k8s/` directory:
```
k8s/
├── namespace.yaml
├── configmap.yaml          # non-secret config
├── secrets.yaml            # sealed secrets (Sealed Secrets or Vault)
├── deployments/
│   ├── web.yaml            # FastAPI, HPA on CPU + request rate
│   ├── worker-tracking.yaml # HPA on tracking_queue depth
│   ├── worker-pricing.yaml  # HPA on scraping_queue depth
│   ├── worker-fx-notify.yaml
│   └── celery-beat.yaml    # single replica, no HPA
├── services/
│   ├── web-service.yaml
│   └── flower-service.yaml
├── ingress/
│   └── nginx-ingress.yaml  # cert-manager for SSL
└── hpa/
    ├── web-hpa.yaml
    └── worker-tracking-hpa.yaml
```

Helm chart for reusable deployment across environments.

KEDA (Kubernetes Event-Driven Autoscaling) for queue-depth-based worker scaling:
```yaml
# Scale workers based on Redis queue depth
triggers:
  - type: redis
    metadata:
      listName: tracking_queue
      listLength: "10"
```

---

### 3.7 Blue-Green Deployment

**Why:** Zero-downtime deployments. Current Docker Compose restarts cause brief service interruption.

**What to build:**

GitHub Actions workflow:
```yaml
deploy:
  steps:
    - name: Build new image
    - name: Push to registry
    - name: Deploy to green environment
    - name: Run smoke tests on green
    - name: Switch load balancer to green
    - name: Keep blue running for 10 minutes (instant rollback)
    - name: Decommission blue
```

Nginx upstream switching between blue and green:
```nginx
upstream fastapi {
    server blue:8000  weight=0;   # drain
    server green:8000 weight=100; # active
}
```

---

### 3.8 Analytics Data Pipeline

**Why:** PostgreSQL handles operational queries well. A dedicated analytics warehouse handles complex multi-tenant business intelligence that would be too slow on the primary.

**What to build:**

Phase 3A — Simple ETL with Celery:
- Nightly Celery task extracts aggregated data from PostgreSQL
- Writes to a separate analytics PostgreSQL schema or DuckDB file
- Grafana queries the analytics schema

Phase 3B — Apache Airflow:
- DAGs for nightly ETL jobs
- Data quality checks
- Alerting on data anomalies

Phase 3C — Event streaming (future):
- Kafka producers in service layer on key events (item_sold, container_arrived)
- Kafka consumers update analytics warehouse in near real-time
- Enables cross-tenant market intelligence (anonymised)

---

## Phase 4 — Market Intelligence & Platform

**Target:** 12–18 months

Phase 4 turns the platform from a logistics tool into a market intelligence network.

---

### 4.1 Marketplace Data Intelligence

When enough tenants are on the platform, anonymised and aggregated data creates proprietary market intelligence no competitor can easily replicate.

**What to build:**

`app/services/market_intelligence_service.py`
- Aggregate pricing data across all tenants (anonymised, no PII)
- Compute market averages per category, condition, and region
- Publish as a premium API feature: `GET /market/intelligence/{category}`

```json
Response:
{
  "category":        "electronics",
  "avg_sale_price":  850.00,
  "price_range":     { "p25": 620.00, "p75": 1100.00 },
  "demand_trend":    "rising",
  "best_margin_condition": "tokunbo",
  "updated_at":      "2024-03-01T00:00:00Z"
}
```

Opt-in for tenants — data sharing agreement required. Available on Professional and Enterprise plans only.

---

### 4.2 Public API Platform

**Why:** Third-party integrations (accounting software, other logistics platforms) dramatically expand the platform's reach.

**What to build:**

API keys system:
```sql
CREATE TABLE api_keys (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT REFERENCES organizations(id),
    key_hash    TEXT UNIQUE,   -- hashed, never stored plain
    name        TEXT,
    scopes      TEXT[],        -- read:containers, write:items, etc.
    last_used   TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

OpenAPI spec published at `GET /api/v2/openapi.json` (versioned, stable contract)

Webhook system:
```sql
CREATE TABLE webhooks (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT REFERENCES organizations(id),
    url         TEXT,
    events      TEXT[],  -- container.arrived, item.sold, etc.
    secret      TEXT,    -- HMAC signing secret
    is_active   BOOLEAN,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

Webhook delivery worker with retry and exponential backoff.

---

### 4.3 Mobile Offline Sync Conflict Resolution

**Why:** Flutter mobile clients queue operations offline. When they reconnect, conflicts arise when the server state has changed.

**What to build:**

Conflict resolution strategies exposed via API:
- `last-write-wins` — default for most fields
- `server-wins` — for financial fields (selling_price, landed_cost)
- `manual` — flag conflicting records for user review

New table:
```sql
CREATE TABLE sync_conflicts (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT REFERENCES organizations(id),
    user_id         BIGINT REFERENCES users(id),
    entity_type     TEXT,
    entity_id       BIGINT,
    client_version  JSONB,   -- what the client tried to write
    server_version  JSONB,   -- what was on the server
    resolution      TEXT,    -- pending / last_write_wins / server_wins / manual
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

`POST /sync/batch` — mobile client submits a batch of queued operations with vector clocks. Server applies non-conflicting operations, returns conflict list for manual resolution.

---

## Dependency Map

```
Phase 1 (complete)
     │
     ├── Phase 2.1 Billing ──────────────────── Phase 4.2 API Platform
     ├── Phase 2.2 Onboarding
     ├── Phase 2.3 RLS ──────────────────────── Phase 3.6 Kubernetes
     ├── Phase 2.4 Read Replica ─────────────── Phase 3.8 Data Pipeline
     ├── Phase 2.5 Elasticsearch
     ├── Phase 2.6 Materialized Views ────────── Phase 3.1 ML Pricing
     ├── Phase 2.7 WebSockets ───────────────── Phase 4.3 Offline Sync
     │
     ├── Phase 3.1 ML Pricing ───────────────── Phase 4.1 Market Intelligence
     ├── Phase 3.2 Demand Forecasting
     ├── Phase 3.3 Cost Simulator
     ├── Phase 3.4 Freight Rates ─────────────── Phase 4.2 API Platform
     ├── Phase 3.5 Supplier Analytics
     ├── Phase 3.6 Kubernetes ───────────────── Phase 3.7 Blue-Green
     └── Phase 3.8 Analytics Pipeline ────────── Phase 4.1 Market Intelligence
```

---

## Estimated Timeline

| Phase | Feature | Effort | Dependency |
|-------|---------|--------|------------|
| 2.1 | Stripe billing | 2 weeks | None |
| 2.2 | Tenant onboarding + invites | 1 week | 2.1 |
| 2.3 | PostgreSQL RLS | 3 days | None |
| 2.4 | Read replica | 2 days | None |
| 2.5 | Elasticsearch | 2 weeks | None |
| 2.6 | Materialized views | 3 days | None |
| 2.7 | WebSockets | 1 week | None |
| 3.1 | ML pricing | 4 weeks | 2.6 + data |
| 3.2 | Demand forecasting | 3 weeks | data |
| 3.3 | Cost simulator | 1 week | None |
| 3.4 | Freight rate comparison | 2 weeks | None |
| 3.5 | Supplier performance | 1 week | None |
| 3.6 | Kubernetes migration | 3 weeks | None |
| 3.7 | Blue-green deployment | 1 week | 3.6 |
| 3.8 | Analytics pipeline | 4 weeks | 2.4 |
| 4.1 | Market intelligence | 4 weeks | 3.1 + data |
| 4.2 | Public API platform | 3 weeks | 2.1 |
| 4.3 | Offline sync conflicts | 2 weeks | None |

> ML features (3.1, 3.2, 4.1) require a minimum of 3 months of sales data before the models have meaningful signal. Build the data collection infrastructure first, train the models later.

---

## Technology Additions by Phase

| Phase | New Technology | Purpose |
|-------|---------------|---------|
| 2 | `stripe` | Subscription billing |
| 2 | `elasticsearch-py` | Full-text search |
| 2 | WebSockets (built into FastAPI) | Live updates |
| 2 | PostgreSQL RLS | Database-level isolation |
| 3 | `scikit-learn` / `xgboost` | ML pricing model |
| 3 | `prophet` / `statsmodels` | Demand forecasting |
| 3 | `onnxruntime` | Model inference |
| 3 | Kubernetes + Helm | Container orchestration |
| 3 | KEDA | Queue-depth autoscaling |
| 3 | Apache Airflow | ETL pipeline orchestration |
| 4 | Apache Kafka | Event streaming |
| 4 | DuckDB or ClickHouse | Analytics warehouse |
| 4 | Vector database (pgvector) | Semantic similarity for pricing |