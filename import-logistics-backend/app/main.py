# app/main.py
import logging
import logging.config
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import settings
from app.core.database import async_engine
from app.middleware.logging_middleware import RequestLoggingMiddleware, MetricsMiddleware
from app.middleware.idempotency_middleware import IdempotencyMiddleware
from app.routers import api_router

# ------------------------------------------------------------------------------
# Logging — JSON in production, readable in development
# ------------------------------------------------------------------------------
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "logging.Formatter",
            "fmt": '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class":     "logging.StreamHandler",
            "formatter": "json" if settings.ENVIRONMENT == "production" else "standard",
        },
    },
    "root": {
        "level":    settings.LOG_LEVEL,
        "handlers": ["console"],
    },
}
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Sentry — only initialised when DSN is provided
# ------------------------------------------------------------------------------
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.2,    # 20 % of requests traced
        send_default_pii=False,
    )
    logger.info("Sentry initialised (env=%s)", settings.ENVIRONMENT)


# ------------------------------------------------------------------------------
# Rate limiter — keyed by IP by default; per-user keying done in routers
# ------------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_API])


# ------------------------------------------------------------------------------
# OpenTelemetry — only when endpoint is configured
# ------------------------------------------------------------------------------
def _setup_otel() -> None:
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        return
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    provider = TracerProvider()
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=async_engine.sync_engine)
    logger.info("OpenTelemetry tracing enabled")


# ------------------------------------------------------------------------------
# Lifespan — startup + shutdown hooks (replaces deprecated @app.on_event)
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting %s (env=%s)", settings.PROJECT_NAME, settings.ENVIRONMENT)

    # Verify DB connectivity
    try:
        async with async_engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("Database connection OK")
    except Exception as e:
        logger.critical("Database connection failed: %s", e)
        raise

    # Verify Redis connectivity
    try:
        import redis.asyncio as aioredis
        r = await aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        logger.info("Redis connection OK")
    except Exception as e:
        logger.critical("Redis connection failed: %s", e)
        raise

    _setup_otel()

    yield   # ── Application runs ─────────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down — disposing DB engine")
    await async_engine.dispose()


# ------------------------------------------------------------------------------
# App instance
# NOTE: create_all is intentionally absent — use `alembic upgrade head`
# ------------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if not settings.ENVIRONMENT == "production" else None,
    default_response_class=ORJSONResponse,   # faster JSON serialisation
    lifespan=lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ------------------------------------------------------------------------------
# Middleware — order matters (outermost = first to receive request)
# ------------------------------------------------------------------------------

# 1. CORS — must be first
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
    )

# 2. Structured request logging + request ID injection
app.add_middleware(RequestLoggingMiddleware)

# 3. Prometheus metrics counter
app.add_middleware(MetricsMiddleware)

# 4. Idempotency cache (POST/PUT/PATCH only)
app.add_middleware(IdempotencyMiddleware)

# ------------------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------------------
app.include_router(api_router, prefix=settings.API_V1_STR)

# ------------------------------------------------------------------------------
# Prometheus metrics scrape endpoint (separate ASGI app — no auth needed)
# Mount AFTER main router so it doesn't interfere with API routes
# ------------------------------------------------------------------------------
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ------------------------------------------------------------------------------
# Health endpoints — outside rate limiter, outside API version prefix
# ------------------------------------------------------------------------------
@app.get("/health", tags=["health"], include_in_schema=False)
async def liveness():
    """Kubernetes liveness probe — always 200 if process is running."""
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/ready", tags=["health"], include_in_schema=False)
async def readiness():
    """
    Kubernetes readiness probe — checks DB + Redis + Celery worker ping.
    Returns 503 if any dependency is unhealthy.
    """
    checks: dict[str, str] = {}
    healthy = True

    # DB
    try:
        async with async_engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        healthy = False

    # Redis
    try:
        import redis.asyncio as aioredis
        r = await aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        healthy = False

    # Celery (inspect active workers — non-blocking)
    try:
        from app.core.celery_app import celery_app
        i = celery_app.control.inspect(timeout=1.0)
        workers = i.ping()
        checks["celery"] = "ok" if workers else "no workers"
        if not workers:
            healthy = False
    except Exception as e:
        checks["celery"] = f"error: {e}"
        healthy = False

    status_code = 200 if healthy else 503
    return ORJSONResponse(
        content={"status": "ready" if healthy else "degraded", "checks": checks},
        status_code=status_code,
    )