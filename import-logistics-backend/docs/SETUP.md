# Setup Guide

## 1. Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Docker + Docker Compose | Recent | Recommended setup; runs the backend, database, Redis and background workers |
| Python | 3.11 | Running without Docker, tests and development |
| PostgreSQL | 16 | Running without Docker |
| Redis | 7 | Running without Docker; separate state and cache instances recommended |
| Flutter | Stable | Only for the legacy mobile application in `../lib` |

## 2. Docker setup (recommended)

Docker Compose is the recommended way to run the backend. It starts PostgreSQL, PgBouncer, Redis, the FastAPI application, Celery workers, Celery Beat and monitoring services.

### First-time setup

From the repository root:

```bash
cd import-logistics-backend
```

Create your environment file:

```bash
cp .env.example .env
```

Edit `.env` and configure the required values.

| Variable | How to configure |
|---|---|
| `SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `POSTGRES_USER` | Database username; default example is `import_user` |
| `POSTGRES_PASSWORD` | Generate a strong, unique password |
| `POSTGRES_DB` | Database name; default example is `import_logistics` |
| `FLOWER_PASSWORD` | Strong password for the Flower dashboard |
| `GRAFANA_PASSWORD` | Strong password for Grafana |
| `FIRST_SUPERUSER_EMAIL` | Email for the initial platform administrator |
| `FIRST_SUPERUSER_USERNAME` | Username for the initial platform administrator |
| `FIRST_SUPERUSER_PASSWORD` | Strong password for the initial platform administrator |

**Database URL:** The example `DATABASE_URL` is constructed using `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB`. You normally do not need to edit it manually when using Docker.

Never commit `.env` to version control.

### Verify migrations

Before starting a new installation, you can verify that the migrations work against a real PostgreSQL database:

```bash
pip install -r requirements-dev.txt
bash scripts/verify_migrations.sh
```

This script uses a throwaway PostgreSQL database. It does not reset your application database.

### Build and start the backend

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d --build
```

The `migrate` service applies the database migrations before the application starts.

Check the services:

```bash
docker compose --env-file .env -f docker/docker-compose.yml ps
```

### Initialize the first organisation and administrator

Run this command only once for a fresh database:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec web \
  python -m scripts.init_db
```

This creates the initial organisation and platform administrator using the `FIRST_SUPERUSER_*` settings in `.env`.

Do not rerun initialization unnecessarily on an existing database.

### Verify backend health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

A successful readiness response should look similar to:

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis_state": "ok",
    "redis_cache": "ok",
    "celery": "ok"
  }
}
```

Open the API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI specification: http://localhost:8000/api/v1/openapi.json

In Swagger UI, use **Authorize** to authenticate with the administrator account created during initialization.

### Prove the backend works end to end

Run the smoke test against the running backend:

```bash
python scripts/smoke_test.py \
  --base-url http://localhost:8000 \
  --username <superuser> \
  --password <password>
```

The smoke test checks application behaviour including tenant isolation, roles, idempotency, exact cost allocation and audit logging.

## 3. Everyday startup and shutdown

After the first successful setup, you do not need to rebuild the Docker images every time you use the backend.

Make sure Docker Desktop is running, then open the backend directory:

```bash
cd import-logistics-backend
```

### Start the existing backend

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d
```

This starts the existing services and reuses available images and persistent volumes.

### Check service status

```bash
docker compose --env-file .env -f docker/docker-compose.yml ps
```

### Check application readiness

```bash
curl http://localhost:8000/ready
```

### View application logs

```bash
docker compose --env-file .env -f docker/docker-compose.yml logs -f web
```

### Stop the backend

```bash
docker compose --env-file .env -f docker/docker-compose.yml stop
```

This stops the services without deleting containers, images or persistent database data.

### Start previously stopped services

```bash
docker compose --env-file .env -f docker/docker-compose.yml start
```

**Important: Protect your database data**

Do not use:

```bash
docker compose down -v
```

unless you intentionally want to remove persistent volumes.

The PostgreSQL volume contains your application database. Removing it can permanently delete your stored organisations, users, containers, items, expenses and other records.

For normal daily use, `up -d`, `stop` and `start` are sufficient.

## 4. Backend service URLs

When running the development Docker stack:

| Service | URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| Swagger documentation | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Readiness endpoint | http://localhost:8000/ready |
| Health endpoint | http://localhost:8000/health |
| Prometheus metrics | http://localhost:8000/metrics/ |
| Flower (Celery monitoring) | http://localhost:5555 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

## 5. Setup without Docker

This option is for developers who want to run PostgreSQL, Redis, FastAPI and Celery directly on their machine.

### Create a virtual environment

From the backend directory:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements-dev.txt
```

Create the environment file:

```bash
cp .env.example .env
```

Configure `.env` for your local services.

Example:

```dotenv
ENVIRONMENT=development

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/importer
DATABASE_PGBOUNCER=false

REDIS_URL=redis://localhost:6379/0
CACHE_REDIS_URL=redis://localhost:6379/2

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

The database URL above assumes a local PostgreSQL database and user named `importer` and `postgres`, respectively. Adjust the credentials to match your installation.

Create the database:

```bash
createdb importer
```

Alternatively, create it using `psql`.

Apply migrations:

```bash
alembic upgrade head
```

Initialize the first organisation and administrator:

```bash
python -m scripts.init_db
```

### Start the application

Start FastAPI:

```bash
uvicorn app.main:app --reload
```

In another terminal, activate the virtual environment and start a Celery worker:

```bash
celery -A app.core.celery_app worker \
  -l info \
  -Q default,fx_queue,tracking_queue,pricing_queue,scraping_queue,notification_queue
```

In another terminal, start Celery Beat:

```bash
celery -A app.core.celery_app beat -l info
```

Make sure PostgreSQL and Redis are running before starting the application.

For local development, the state and cache Redis services can be separate instances or appropriately isolated Redis databases, depending on the configuration.

## 6. Environment variable reference

The `.env.example` file documents the application's environment variables.

| Group | Variables |
|---|---|
| App | `ENVIRONMENT`, `DEBUG`, `LOG_LEVEL`, `BACKEND_CORS_ORIGINS` |
| Security | `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_MINUTES`, `MAX_LOGIN_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES`, `REGISTRATION_OPEN` |
| Database | `DATABASE_URL`, `DATABASE_PGBOUNCER`, `ALEMBIC_DATABASE_URL`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` |
| Redis | `REDIS_URL`, `CACHE_REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_PASSWORD` |
| Idempotency | `IDEMPOTENCY_KEY_TTL`, `IDEMPOTENCY_LOCK_TTL`, `IDEMPOTENCY_FAIL_CLOSED` |
| Rates | `EXCHANGERATE_API_URL`, `FX_ALLOW_FALLBACK` |
| Tracking | `MSC_API_KEY`, `MSC_API_URL` |
| Scraping | `SCRAPING_ENABLED`, `SCRAPING_USER_AGENT` |
| Email | `EMAIL_PROVIDER`, `SMTP_*`, `SENDGRID_API_KEY`, `MAILGUN_*` |
| Storage | `STORAGE_BACKEND`, `UPLOAD_DIR`, `S3_*`, `R2_*` |
| Bootstrap | `FIRST_SUPERUSER_EMAIL`, `FIRST_SUPERUSER_USERNAME`, `FIRST_SUPERUSER_PASSWORD` |
| Observability | `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT` |

Docker Compose also uses infrastructure-specific variables such as `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `FLOWER_PASSWORD`, `GRAFANA_PASSWORD` and `DOMAIN`.

`BACKEND_CORS_ORIGINS` must be a JSON list of allowed origins. CORS is generally unnecessary when the frontend and API are served from the same origin.

## 7. Running the tests

### Static checks

These scripts can run without installing application dependencies:

```bash
python scripts/check_imports.py
python scripts/check_names.py
python scripts/check_migration.py
```

### Unit tests

```bash
pytest -q
```

### PostgreSQL integration tests

Set `TEST_DATABASE_URL` to a dedicated test database:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test pytest -q
```

Do not point integration tests at your production or development application database.

### Migration checks

```bash
alembic upgrade head
alembic check
```

The models and migrations should agree.

### Smoke tests

With the backend running:

```bash
python scripts/smoke_test.py \
  --base-url http://localhost:8000 \
  --username <superuser> \
  --password <password>
```

The smoke test creates temporary test organisations and exercises important application workflows.

## 8. Production deployment

Production uses a separate Compose file:

```text
docker/docker-compose.prod.yml
```

### Prepare the server

1. Provision a server. Two vCPUs and 4 GB RAM are a sensible starting point.
2. Install Docker and Docker Compose.
3. Point your domain to the server.
4. Configure TLS certificates in the location expected by `docker/nginx`.
5. Create a production `.env` file.

### Production environment

Set:

```dotenv
ENVIRONMENT=production
```

Configure strong, unique secrets and database credentials.

The application refuses to start with missing or weak production secrets, default database credentials or `DEBUG=true`.

Required production configuration includes:

- `SECRET_KEY`
- Strong PostgreSQL credentials
- `REDIS_PASSWORD`
- `BACKEND_CORS_ORIGINS`, where applicable
- `SENTRY_DSN`, if using Sentry
- A production storage backend such as S3 or R2
- `MSC_API_KEY`, if using live carrier tracking

Ensure Redis authentication is configured consistently across the Redis server, application URLs and Celery URLs. Do not enable a Redis password in only one component.

### Start the production stack

```bash
docker compose --env-file .env -f docker/docker-compose.prod.yml up -d --build
```

Check the services:

```bash
docker compose --env-file .env -f docker/docker-compose.prod.yml ps
```

Initialize the first organisation and administrator only for a fresh production database:

```bash
docker compose --env-file .env -f docker/docker-compose.prod.yml exec web \
  python -m scripts.init_db
```

Configure monitoring against `/ready` and alert when the endpoint returns HTTP 503.

Schedule regular database backups and verify that they can be restored.

Pin production image versions, particularly PgBouncer, rather than relying on `latest`.

### Zero-downtime updates

For deployments that require minimal downtime:

1. Build the new application image.
2. Ensure migrations are backward compatible with the currently running application.
3. Run the migration service.
4. Restart application replicas gradually.
5. Verify readiness and application logs.
6. Confirm background workers are processing tasks.

Do not run destructive migrations while older application instances still depend on the affected schema.

### The web app in production

The `nginx` service builds the frontend and serves it together with the API on one origin. This avoids cross-origin cookie issues and allows the refresh cookie to work correctly.

Create or install TLS certificates in:

```text
import-logistics-backend/docker/nginx/ssl/
```

For a local first test, a self-signed certificate can be generated:

```bash
cd import-logistics-backend/docker/nginx/ssl

openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/CN=localhost"
```

Return to the repository root and start the production stack:

```bash
cd ../../../..

docker compose --env-file import-logistics-backend/.env \
  -f import-logistics-backend/docker/docker-compose.prod.yml \
  up -d --build
```

Initialize the database only if it is a fresh installation:

```bash
docker compose --env-file import-logistics-backend/.env \
  -f import-logistics-backend/docker/docker-compose.prod.yml \
  exec web python -m scripts.init_db
```

Open:

```text
https://localhost
```

Production notes:

- The image build runs `npm run build`, which type-checks before building.
- Commit `frontend/package-lock.json` after the first `npm install` to make builds reproducible.
- The strict Content Security Policy allows scripts only from the application's own origin.
- Nginx responds to rate-limited requests with HTTP 429.
- The API limit is 300 requests per minute per address with a burst of 60; sign-in is limited to 5 requests per minute.
- `ENVIRONMENT=production` makes the session cookie HTTPS-only. TLS is therefore required.

## 9. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `/ready` reports schema missing | Migrations have not run. Inspect the `migrate` service logs or run `alembic upgrade head` in the appropriate environment. |
| App exits at startup in production | Inspect logs for production validation failures involving `SECRET_KEY`, `DATABASE_URL` or `DEBUG`. |
| `prepared statement ... does not exist` | Check that `DATABASE_PGBOUNCER=true` when using transaction pooling. |
| `NOAUTH Authentication required` | The Redis URL may be missing the password. Use the appropriate authenticated Redis URL. |
| `503 Exchange rate service unavailable` | The exchange-rate API may be unreachable and fallback may be disabled. |
| `409` on a POST | The same idempotency key may still be processing. Retry after `Retry-After`. |
| `422 Idempotency-Key was already used` | The same key was reused with a different request body. Generate a new key. |
| Tokens suddenly invalid on some requests | Ensure all application containers use the same `SECRET_KEY`. |
| Tracking shows mock data | `MSC_API_KEY` may not be configured. Mock data is for development only. |
| Celery tasks never run | Check that the relevant worker listens to the task's queue and that Celery Beat is running. |
| Worker health check fails | Inspect worker logs and verify that Celery workers can communicate through the configured broker. |
| Database authentication fails after password rotation | Ensure the PostgreSQL role password, Compose environment and application `DATABASE_URL` agree. Recreate services that need the updated credentials. |

Useful log commands:

```bash
docker compose --env-file .env -f docker/docker-compose.yml logs -f web

docker compose --env-file .env -f docker/docker-compose.yml logs -f db

docker compose --env-file .env -f docker/docker-compose.yml logs -f celery-beat

docker compose --env-file .env -f docker/docker-compose.yml logs -f worker-tracking
```

## 10. Common commands

Run these from the backend directory.

### Docker Compose

```bash
# Start the stack
docker compose --env-file .env -f docker/docker-compose.yml up -d

# Rebuild and start after code or Dockerfile changes
docker compose --env-file .env -f docker/docker-compose.yml up -d --build

# Stop without deleting data
docker compose --env-file .env -f docker/docker-compose.yml stop

# Restart stopped services
docker compose --env-file .env -f docker/docker-compose.yml start

# Check services
docker compose --env-file .env -f docker/docker-compose.yml ps

# Follow backend logs
docker compose --env-file .env -f docker/docker-compose.yml logs -f web
```

### Database

Connect to the application database:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec db \
  psql -U import_user -d import_logistics
```

Create a new migration after changing a model:

```bash
alembic revision --autogenerate -m "add something"
```

Apply migrations:

```bash
alembic upgrade head
```

Undo the last migration in development only:

```bash
alembic downgrade -1
```

Before applying or reverting migrations, make sure the correct database is configured and backed up where appropriate.

### Celery

Inspect active workers:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec worker-tracking \
  celery -A app.core.celery_app inspect ping
```

Inspect active queues:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec worker-tracking \
  celery -A app.core.celery_app inspect active_queues
```

Inspect registered tasks:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec worker-tracking \
  celery -A app.core.celery_app inspect registered
```

---

**Security reminder:** Never commit `.env`, private keys, TLS certificates or production credentials to Git. Keep database backups separate from the application source code.