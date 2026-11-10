# Setup Guide

## 1. Prerequisites

| Tool | Version | Needed for |
|------|---------|------------|
| Docker + Docker Compose | recent | Easiest path; also used to generate the baseline migration |
| Python | 3.11 | Running without Docker, tests |
| PostgreSQL | 16 | Without Docker |
| Redis | 7 | Without Docker (two instances recommended: state + cache) |
| Flutter | stable | Only for the mobile/web client in `../lib` |

## 2. Docker setup (recommended)

```bash
git clone <your-repo-url> && cd Importer-main/import-logistics-backend
cp .env.example .env
```

Edit `.env` and set at least:

| Variable | How |
|----------|-----|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `POSTGRES_PASSWORD` | strong password; also update it inside `DATABASE_URL` |
| `FLOWER_PASSWORD`, `GRAFANA_PASSWORD` | strong passwords |
| `FIRST_SUPERUSER_EMAIL`, `_USERNAME`, `_PASSWORD` | your first admin account |

```bash
# 1. One time: prove the migrations work on a real empty PostgreSQL (needs Docker + pip install -r requirements-dev.txt)
bash scripts/verify_migrations.sh      # no Docker? see the header of that script (it can use your own PostgreSQL)

# 2. Start everything (the "migrate" service applies the schema first)
docker compose -f docker/docker-compose.yml up -d --build

# 3. Create the first organisation and admin
docker compose -f docker/docker-compose.yml exec web python -m scripts.init_db

# 4. Check
curl http://localhost:8000/health
curl http://localhost:8000/ready

# 5. Prove it works end to end (tenant isolation, roles, idempotency, exact allocation, audit trail)
python scripts/smoke_test.py --base-url http://localhost:8000 --username <superuser> --password <password>
```

Open http://localhost:8000/docs, click **Authorize**, and log in with the admin from step 3.

## 3. Setup without Docker

```bash
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Set in `.env` (adjust to your local services):

```
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/importer
DATABASE_PGBOUNCER=false
REDIS_URL=redis://localhost:6379/0
CACHE_REDIS_URL=redis://localhost:6379/2
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

```bash
createdb importer                      # or use psql
alembic upgrade head                   # applies alembic/versions/001_baseline.py
python -m scripts.init_db
uvicorn app.main:app --reload          # API
celery -A app.core.celery_app worker -l info -Q default,fx_queue,tracking_queue,pricing_queue,scraping_queue,notification_queue
celery -A app.core.celery_app beat -l info
```

## 4. Environment variable reference

| Group | Variables |
|-------|-----------|
| App | `ENVIRONMENT` (development/staging/production), `DEBUG`, `LOG_LEVEL`, `BACKEND_CORS_ORIGINS` (JSON list of origins) |
| Security | `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_MINUTES`, `MAX_LOGIN_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES`, `REGISTRATION_OPEN` |
| Database | `DATABASE_URL`, `DATABASE_PGBOUNCER`, `ALEMBIC_DATABASE_URL`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` |
| Redis | `REDIS_URL` (state), `CACHE_REDIS_URL` (cache), `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_PASSWORD` (prod compose) |
| Idempotency | `IDEMPOTENCY_KEY_TTL`, `IDEMPOTENCY_LOCK_TTL`, `IDEMPOTENCY_FAIL_CLOSED` |
| Rates | `EXCHANGERATE_API_URL`, `FX_ALLOW_FALLBACK` |
| Tracking | `MSC_API_KEY`, `MSC_API_URL` |
| Scraping | `SCRAPING_ENABLED`, `SCRAPING_USER_AGENT` |
| Email | `EMAIL_PROVIDER`, `SMTP_*`, `SENDGRID_API_KEY`, `MAILGUN_*` |
| Storage | `STORAGE_BACKEND`, `UPLOAD_DIR`, `S3_*`, `R2_*` |
| Bootstrap | `FIRST_SUPERUSER_EMAIL`, `FIRST_SUPERUSER_USERNAME`, `FIRST_SUPERUSER_PASSWORD` |
| Observability | `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT` |

`.env.example` documents every variable with a comment.

## 5. Running the tests

Besides the automated tests, `python scripts/check_imports.py` and `python scripts/check_names.py` need no installed packages and catch broken imports and undefined names. `scripts/smoke_test.py` runs about 65 end-to-end checks against a running stack (it creates two throw-away organisations).

```bash
pytest -q                               # unit + HTTP-level tests, no external services needed
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test pytest -q   # adds the PostgreSQL tests
alembic upgrade head && alembic check   # models and migrations must agree
python scripts/check_migration.py       # offline version of the same check (no database needed)
```

## 6. Production deployment

1. Provision a server (2 vCPU / 4 GB is a sensible start), install Docker, point a domain at it, and put TLS certificates where `docker/nginx` expects them (Let's Encrypt works well).
2. Create `.env` with `ENVIRONMENT=production`. The app **refuses to start** with a missing/weak `SECRET_KEY`, default database credentials or `DEBUG=true`.
3. Required extras in production: `REDIS_PASSWORD`, `BACKEND_CORS_ORIGINS`, `SENTRY_DSN`, a real `STORAGE_BACKEND` (s3/r2), and `MSC_API_KEY` if you want tracking.
4. `docker compose -f docker/docker-compose.prod.yml up -d --build`
5. `docker compose -f docker/docker-compose.prod.yml exec web python -m scripts.init_db`
6. Point your monitor at `/ready` and alert on 503. Pin image versions (especially PgBouncer) and schedule database backups.

**Zero-downtime updates:** build the new image, run `migrate` (migrations must be backward compatible with the running version), then restart `web` replicas one at a time.

### The web app in production

The `nginx` service now builds the frontend and serves it together with the API on ONE origin (so there is no CORS, and the
refresh cookie works). From the repository root:

```bash
# TLS certificate (a self-signed one is fine for a first test; browsers warn once)
cd import-logistics-backend/docker/nginx/ssl
openssl req -x509 -nodes -newkey rsa:2048 -days 30 -keyout privkey.pem -out fullchain.pem -subj "/CN=localhost"
cd ../../../..

docker compose -f import-logistics-backend/docker/docker-compose.prod.yml --env-file import-logistics-backend/.env up -d --build
docker compose -f import-logistics-backend/docker/docker-compose.prod.yml exec web python -m scripts.init_db
# then open https://localhost
```

What to know:
* The image build runs `npm run build`, which type-checks first: a type error fails the build instead of shipping a broken app.
* Commit `frontend/package-lock.json` after your first `npm install` so builds are reproducible.
* Scripts may only come from your own origin (strict Content-Security-Policy), so there are no inline scripts anywhere.
* Nginx now answers rate-limited requests with **429** (it used to send 503, which looks like an outage). The API limit is 300
  requests a minute per address with a burst of 60; sign-in stays at 5 a minute. A whole office behind one address shares these.
* `ENVIRONMENT=production` makes the session cookie HTTPS-only, which is why TLS is required.

## 7. Troubleshooting

| Symptom | Likely cause and fix |
|---------|----------------------|
| `/ready` returns `schema missing` | Migrations have not run: `alembic upgrade head` (or check the `migrate` service logs) |
| App exits at start in production | A production check failed: read the log line (SECRET_KEY, DATABASE_URL credentials, DEBUG) |
| `prepared statement ... does not exist` | Using PgBouncer without `DATABASE_PGBOUNCER=true` |
| `NOAUTH Authentication required` | Redis URL is missing the password (`redis://:PASSWORD@host:6379/0`) |
| `503 Exchange rate service unavailable` | Rate API unreachable and fallback disabled in production |
| `409` on a POST | Same `Idempotency-Key` still being processed; retry after `Retry-After` |
| `422 Idempotency-Key was already used...` | You reused a key with a different request body: generate a new key |
| Tokens suddenly invalid on some requests | `SECRET_KEY` differs between containers; it must be identical everywhere |
| Tracking shows mock data | `MSC_API_KEY` not set (development only; production reports unavailable) |
| Celery tasks never run | Worker not listening on that queue, or beat not running |

## 8. Common commands

```bash
docker compose -f docker/docker-compose.yml logs -f web           # API logs
docker compose -f docker/docker-compose.yml exec db psql -U postgres importer
alembic revision --autogenerate -m "add something"                # new migration after a model change
alembic downgrade -1                                              # undo the last migration (dev only)
```
