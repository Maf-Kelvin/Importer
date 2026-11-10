# Import Profit & Logistics Intelligence System

A production-grade SaaS backend for managing import containers, tracking shipments, calculating landed costs, and optimising pricing strategies. Built with FastAPI, PostgreSQL, Redis, and Celery.

---

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Project Structure](#project-structure)

---

## Features

### Core Logistics
- Container management (20ft / 40ft) with full expense tracking
- Automatic cost allocation — weight-based or value-based
- Multi-currency support (USD, EUR, CZK, NGN) with live FX rates
- MSC container tracking with real-time status updates
- Shipment timeline with transport legs and port data

### Pricing Intelligence
- Cost-based pricing with configurable profit margins
- Market price scraping from Jiji, eBay, Mobile.de, AutoScout24, Bazos.cz
- Confidence-weighted price recommendations
- Historical price tracking and demand analytics

### Warehouse & Inventory
- Multi-warehouse inventory management
- Stock movement tracking (in / out / transfer / adjust)
- Low stock alerts via automated Celery tasks

### Sales & Commerce
- Customer and order management
- Dedicated Sale records per item
- Payment tracking across orders and containers
- Supplier management with ratings

### Security & Access
- JWT access + refresh tokens with Redis-backed blacklist
- Role-based access control (Admin, Manager, Clerk, Viewer)
- Account lockout after configurable failed login attempts
- Multi-tenant data isolation via `tenant_id` on every table
- Idempotency keys for safe mobile client retries

### Observability
- Structured JSON request logging with correlation IDs
- Prometheus metrics at `/metrics`
- Sentry error tracking
- OpenTelemetry distributed tracing
- Celery task monitoring via Flower

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| API framework | FastAPI 0.104 |
| Language | Python 3.11+ |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Connection pooling | PgBouncer |
| Cache & queue | Redis 7 |
| Background tasks | Celery 5.3 |
| Task monitoring | Flower |
| Production server | Gunicorn + UvicornWorker |
| Reverse proxy | Nginx |
| Containerisation | Docker + Docker Compose |
| Monitoring | Prometheus + Grafana |
| Error tracking | Sentry |
| Tracing | OpenTelemetry |
| Storage | Local / AWS S3 / Cloudflare R2 |
| Email | SMTP / SendGrid / Mailgun / SES |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development only)

### 1. Clone and configure

```bash
git clone <repository-url>
cd import-logistics-backend
cp .env.example .env
```

Edit `.env` and set all required values (marked with comments).

### 2. Start all services

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### 3. Run database migrations

```bash
docker-compose -f docker/docker-compose.yml exec web alembic upgrade head
```

### 4. Access the application

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |
| Readiness check | http://localhost:8000/ready |
| Celery monitoring | http://localhost:5555 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

### 5. Local development (without Docker)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start PostgreSQL and Redis separately, then:
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# In separate terminals:
celery -A app.core.celery_app worker --queues=tracking_queue --loglevel=info
celery -A app.core.celery_app worker --queues=pricing_queue,scraping_queue --loglevel=info
celery -A app.core.celery_app worker --queues=fx_queue,notification_queue --loglevel=info
celery -A app.core.celery_app beat --loglevel=info
```

---

## Environment Variables

All variables are documented in `.env.example`. Key required variables:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key — generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `DATABASE_URL` | Full async database URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis connection URL |
| `FLOWER_PASSWORD` | Flower UI password |
| `GRAFANA_PASSWORD` | Grafana admin password |

Optional but recommended for production:

| Variable | Description |
|----------|-------------|
| `SENTRY_DSN` | Sentry error tracking DSN |
| `EXCHANGERATE_API_KEY` | Live FX rates |
| `MSC_API_KEY` | MSC container tracking |
| `SENDGRID_API_KEY` | Email via SendGrid |

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Roll back one migration
alembic downgrade -1

# View migration history
alembic history

# Check current revision
alembic current
```

> **Important:** Never use `Base.metadata.create_all()` in production.
> Always use Alembic migrations for schema changes.

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test module
pytest app/tests/test_containers.py -v

# Run with async support
pytest --asyncio-mode=auto
```

---

## Deployment

### Production with Docker Compose

```bash
# Build and start production stack
docker-compose -f docker/docker-compose.prod.yml up -d --build

# Run migrations
docker-compose -f docker/docker-compose.prod.yml exec web alembic upgrade head

# Scale web workers
docker-compose -f docker/docker-compose.prod.yml up -d --scale web=3

# Scale Celery tracking workers
docker-compose -f docker/docker-compose.prod.yml up -d --scale worker-tracking=2

# View logs
docker-compose -f docker/docker-compose.prod.yml logs -f web
```

### SSL Certificates

Place your SSL certificate files in `docker/nginx/ssl/`:

```
docker/nginx/ssl/fullchain.pem
docker/nginx/ssl/privkey.pem
```

For Let's Encrypt, use Certbot and copy the certificates to that directory.

### Production Checklist

- [ ] Set a strong random `SECRET_KEY`
- [ ] Set strong passwords for all services
- [ ] Configure `BACKEND_CORS_ORIGINS` to your frontend domain only
- [ ] Set `ENVIRONMENT=production` and `DEBUG=false`
- [ ] Configure `SENTRY_DSN` for error tracking
- [ ] Set up SSL certificates in `docker/nginx/ssl/`
- [ ] Configure email provider (`EMAIL_PROVIDER` + credentials)
- [ ] Set up object storage for file uploads (`STORAGE_BACKEND=s3` or `r2`)
- [ ] Configure `EXCHANGERATE_API_KEY` for live FX rates
- [ ] Set up automated database backups
- [ ] Review and restrict `BACKEND_CORS_ORIGINS`

---

## Project Structure

```
import-logistics-backend/
├── app/
│   ├── main.py                         # FastAPI app, middleware, lifespan
│   ├── core/
│   │   ├── config.py                   # Settings (pydantic-settings)
│   │   ├── database.py                 # Async engine, session, transaction helper
│   │   ├── security.py                 # JWT, bcrypt, token blacklist, lockout
│   │   ├── celery_app.py               # Celery config, queues, beat schedule
│   │   └── redis_lock.py               # Distributed lock (async + sync)
│   ├── models/                         # SQLAlchemy ORM models
│   │   ├── base.py                     # BaseModel, SoftDeleteModel, mixins
│   │   ├── organization.py             # Multi-tenant foundation
│   │   ├── user.py                     # Users, roles, lockout fields
│   │   ├── container.py                # Containers (soft-delete)
│   │   ├── item.py                     # Items (soft-delete)
│   │   ├── expense.py                  # Container expenses
│   │   ├── pricing.py                  # Price records
│   │   ├── tracking.py                 # Tracking records
│   │   ├── logistics.py                # Shipment, Port, TransportLeg, Document, Customs
│   │   ├── warehouse.py                # Warehouse, Inventory, Movements
│   │   ├── commerce.py                 # Customer, Supplier, Order, Payment, Sale
│   │   └── analytics.py                # FX history, Notifications, AuditLog, Demand
│   ├── schemas/                        # Pydantic request/response schemas
│   ├── routers/                        # FastAPI route handlers
│   ├── services/                       # Business logic layer
│   │   ├── auth_service.py
│   │   ├── container_service.py
│   │   ├── pricing_service.py
│   │   ├── tracking_service.py
│   │   ├── cost_allocation_service.py
│   │   ├── fx_service.py
│   │   ├── notification_service.py
│   │   ├── scraper_service.py
│   │   ├── cache_service.py
│   │   └── file_service.py
│   ├── workers/                        # Celery background tasks
│   │   ├── fx_worker.py
│   │   ├── tracking_worker.py
│   │   ├── pricing_worker.py
│   │   └── notification_worker.py
│   ├── middleware/
│   │   ├── logging_middleware.py       # Structured JSON request logs
│   │   └── idempotency_middleware.py   # Idempotency key handling
│   └── tests/
├── alembic/                            # Database migrations
├── docker/
│   ├── Dockerfile                      # Multi-stage dev/prod build
│   ├── docker-compose.yml              # Development stack
│   ├── docker-compose.prod.yml         # Production stack
│   ├── gunicorn.conf.py                # Gunicorn production config
│   ├── nginx/
│   │   └── nginx.conf                  # Reverse proxy, SSL, rate limiting
│   └── prometheus.yml                  # Prometheus scrape config
├── .env.example                        # Environment variable template
├── requirements.txt
└── README.md
```