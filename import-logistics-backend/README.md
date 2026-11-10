# Import Profit & Logistics Intelligence System - Backend

A multi-tenant REST API for businesses that import goods in shipping containers.
It records containers, items and expenses, spreads shared costs across items to
give an exact landed cost per item, recommends selling prices, tracks shipments,
and reports profit.

**Stack:** Python 3.11, FastAPI, async SQLAlchemy 2, PostgreSQL 16 (via PgBouncer),
Redis, Celery, Alembic, Docker Compose, Prometheus / Sentry / OpenTelemetry.
A Flutter client lives in [`../lib`](../lib).

> Docs: [Setup](docs/SETUP.md) | [API](docs/API.md) | [Database](docs/DATABASE.md) | [Integrations](docs/INTEGRATIONS.md) | [Pricing](docs/PRICING.md) | [Architecture](docs/ARCHITECTURE.md)

---

## What it does

| Area | Capability |
|------|------------|
| Containers & items | Create containers, add items in any supported currency (USD, EUR, CZK, NGN), seal containers |
| Expenses | Loading, shipping, clearing, warehouse, security fees, converted to USD at the rate of the day |
| Cost allocation | Spread shared expenses over items by **weight** or **value**; shares add up to the total exactly |
| Pricing | Explainable recommendation: USD-normalised market comparables, outlier removal, recency weighting, blended with cost-plus, minimum-margin floor, price band, confidence and an accuracy report ([PRICING.md](docs/PRICING.md)) |
| Tracking | Shipment status updates from the carrier API, with notifications |
| Reports | Dashboard, per-container and per-category profit, demand analytics |
| Security | JWT access/refresh tokens with rotation, role-based access (admin, manager, clerk, viewer), tenant isolation, login lockout, rate limits |
| Auditability | Append-only audit trail of every money-related and user change (`GET /audit-logs/`) |
| Onboarding | Platform administrator creates organisations with their first admin (`POST /organizations/`) |
| Reliability | Idempotent writes, background jobs on separate queues, health and readiness probes |

---

## Quick start (Docker)

```bash
cd import-logistics-backend
cp .env.example .env
# Fill in the REQUIRED values in .env:
#   SECRET_KEY            python -c "import secrets; print(secrets.token_urlsafe(64))"
#   POSTGRES_PASSWORD, FLOWER_PASSWORD, GRAFANA_PASSWORD
#   FIRST_SUPERUSER_EMAIL / _USERNAME / _PASSWORD (to create your first admin)

docker compose -f docker/docker-compose.yml up -d --build
# The one-shot "migrate" service applies the database schema before the API starts.

docker compose -f docker/docker-compose.yml exec web python -m scripts.init_db
```

| URL | What |
|-----|------|
| http://localhost:8000/docs | Interactive API docs (disabled when `ENVIRONMENT=production`) |
| http://localhost:8000/health | Liveness |
| http://localhost:8000/ready | Readiness (database + schema, state Redis; reports cache and workers) |
| http://localhost:8000/metrics | Prometheus metrics |
| http://localhost:5555 | Flower (Celery monitoring) |

There is **no default login**. The first admin is created by `scripts/init_db.py`
from the `FIRST_SUPERUSER_*` variables.

## Local development (without Docker)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # point DATABASE_URL / REDIS_URL at your local services
alembic upgrade head
python -m scripts.init_db
uvicorn app.main:app --reload
# separate terminals:
celery -A app.core.celery_app worker --loglevel=info
celery -A app.core.celery_app beat   --loglevel=info
```

---

## Database migrations

`alembic/versions/001_baseline.py` creates the whole schema (26 tables, 17 enum types, 100 indexes). Docker Compose
runs `alembic upgrade head` in a one-shot `migrate` service before the API starts.

**Status:** verified on a real PostgreSQL 16 (upgrade, `alembic check` reporting no differences, downgrade to base,
upgrade again). The file was generated from the models and is also checked offline by
`python scripts/check_migration.py`, which compares every table, column, type, foreign key, index, constraint and
enum with the models. Re-run the real check any time with:

```bash
bash scripts/verify_migrations.sh     # throw-away PostgreSQL: upgrade, check, downgrade, upgrade again
```

If `alembic check` reports differences, add a follow-up migration (`alembic revision --autogenerate -m "sync"`).
Day to day: after any model change run `alembic revision --autogenerate -m "what changed"`; CI fails if the
models and migrations disagree.

---

## Configuration

Copy `.env.example`; every setting is documented there. The ones that matter most:

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | `development`, `staging` or `production`. Production **refuses to start** with a missing/short `SECRET_KEY`, default database credentials, or `DEBUG=true` |
| `SECRET_KEY` | JWT signing key, at least 32 random characters. Must be identical across all containers |
| `DATABASE_URL` | Async URL (`postgresql+asyncpg://...`), normally via PgBouncer |
| `DATABASE_PGBOUNCER` | `true` when `DATABASE_URL` goes through PgBouncer (turns off asyncpg prepared statements) |
| `ALEMBIC_DATABASE_URL` | Direct PostgreSQL URL used by migrations (bypasses PgBouncer) |
| `REDIS_URL` | **State** Redis: Celery broker, locks, idempotency keys, token blacklist. Run with `noeviction` |
| `CACHE_REDIS_URL` | **Cache** Redis: dashboards, FX rates. Run with `allkeys-lru`. Falls back to `REDIS_URL` in development |
| `MSC_API_KEY` | Carrier tracking. Without it, development uses mock data; **production reports tracking as unavailable** |
| `FX_ALLOW_FALLBACK` | Allow hard-coded fallback exchange rates in production (default `false`: fail with 503 instead) |
| `IDEMPOTENCY_FAIL_CLOSED` | If Redis is down, reject writes that carry an `Idempotency-Key` (default `true`) |

---

## Working with money

* Money is `Decimal` in Python and `NUMERIC(18,4)` in PostgreSQL; FX rates are `NUMERIC(18,8)`;
  weights and volumes are `NUMERIC(12,3)`. Floats are not used for amounts.
* Amounts are accepted with up to 4 decimal places; more is a validation error.
* In JSON responses amounts are numbers (so the Flutter client keeps working).
  To return strings instead, change the serializer in `app/schemas/types.py`.
* Cost allocation uses the largest-remainder method: the per-item shares always add
  up to the expense total exactly. The container row is locked during allocation, and
  all items are updated in one transaction.
* If you edit an item's price/weight or an expense after allocating, call
  `POST /containers/{id}/allocate-costs` again.

## Idempotent writes

Send an `Idempotency-Key` header (8 to 128 characters; a UUID is ideal) with
`POST`/`PUT`/`PATCH`. Behaviour:

| Situation | Result |
|-----------|--------|
| First request | Runs normally; a 2xx response is stored for 24 h |
| Same key, same request | Stored response replayed, header `Idempotent-Replayed: true` |
| Same key, different request | `422` |
| Same key, first request still running | `409` with `Retry-After` |
| First request failed (non-2xx) | Key released; the client may retry |
| Redis unavailable | `503` (or unprotected, if `IDEMPOTENCY_FAIL_CLOSED=false`) |

Keys are scoped to the authenticated tenant and user. Redis is the only store, so
operations that move money must also be protected by a database unique constraint.

---

## Testing

```bash
pip install -r requirements-dev.txt
python scripts/check_imports.py && python scripts/check_names.py && python scripts/check_migration.py   # static checks, no packages needed
pytest -q                                   # unit + HTTP-level tests (no external services)

# include the PostgreSQL integration tests:
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test pytest -q
```

| File | Covers |
|------|--------|
| `app/tests/test_money.py` | Decimal conversion, rounding, exact proportional allocation |
| `app/tests/test_idempotency_store.py` | Claim / replay / mismatch / release / crash-expiry state machine |
| `app/tests/test_idempotency_middleware.py` | The same rules end-to-end over HTTP, including simultaneous duplicates |
| `app/tests/test_audit_utils.py` | Audit diff, JSON-safety and redaction |
| `app/tests/test_pricing_math.py` | Price engine: outliers, recency, floor, confidence, accuracy metrics |
| `app/tests/test_reporting.py` | Profit definitions |
| `scripts/check_imports.py`, `scripts/check_names.py`, `scripts/check_migration.py` | Static checks, no packages needed: imports resolve, no undefined names, migrations match the models |
| `scripts/smoke_test.py` | ~65 end-to-end checks on a running stack: tenant isolation, roles, idempotency, reports, pricing, files |
| `app/tests/test_cost_allocation_integration.py` | Allocation against real PostgreSQL, concurrency, tenant isolation |

CI (`.github/workflows/ci.yml`) runs all of the above plus `alembic upgrade head` and `alembic check`.

---

## Deploying

```bash
docker compose -f docker/docker-compose.prod.yml up -d --build
```

* A one-shot `migrate` service runs `alembic upgrade head` before the API starts.
* Nginx terminates TLS and rate-limits; the API is not exposed directly.
* Two Redis instances: `redis` (durable, `noeviction`, password) and `redis-cache` (LRU).
* Pin the PgBouncer image version before going live (`bitnami/pgbouncer:latest` is not reproducible).

Production checklist: strong `SECRET_KEY`, `REDIS_PASSWORD`, real `MSC_API_KEY` (or accept
that tracking is off), `BACKEND_CORS_ORIGINS` set to your front-end origins, `SENTRY_DSN`,
database backups, and an alert on `/ready` returning 503.

---

## Project layout

```
app/
  main.py               app, middleware stack, probes
  core/                 config, database, security, redis clients, idempotency, celery, locks
  middleware/           request logging, metrics, idempotency (pure ASGI)
  routers/              HTTP layer: thin, validates input, calls services
  services/             business logic (containers, cost allocation, pricing, tracking, FX)
  models/               SQLAlchemy models (tenant_id on every business table)
  schemas/              Pydantic request/response models (+ Money/Rate/Weight types)
  workers/              Celery tasks (fx, tracking, pricing, notifications)
  utils/money.py        Decimal helpers and exact allocation
  tests/
alembic/                migrations
docker/                 Dockerfile, compose files, nginx, gunicorn, prometheus
scripts/                init_db, create_admin, verify_migrations.sh, check_*.py, smoke_test.py
```

## Known limitations

* Scraped market prices are matched by name and are noisy; the pricing engine limits the damage but cannot remove it (see `docs/PRICING.md`).
* Market prices come from scraping and are stored as floats (estimates, not accounting data).
* About a dozen tables (suppliers, orders, payments, shipments, warehouses, customs) exist in the schema but have no API yet.
* Carrier tracking has only been exercised against mock data; verify with a real `MSC_API_KEY`.
* Idempotency is durable (PostgreSQL) but completed after the endpoint commits; for payments also add a natural unique key on the business row.
* Celery tasks use `acks_late`, so a task can run twice after a worker crash and must stay safe to repeat.
