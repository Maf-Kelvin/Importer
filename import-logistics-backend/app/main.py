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
from app.core.redis_clients import close_redis_clients
from app.middleware.request_context_middleware import RequestContextMiddleware
from app.services.fx_service import FXRateUnavailable
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
    logger.info("Shutting down — closing Redis and disposing DB engine")
    await close_redis_clients()
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


@app.exception_handler(FXRateUnavailable)
async def fx_unavailable_handler(request: Request, exc: FXRateUnavailable):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=503,
        content={"detail": "Exchange rate service unavailable, please retry later"},
        headers={"Retry-After": "30"},
    )

# ------------------------------------------------------------------------------
# Middleware — Starlette wraps in REVERSE: the LAST one added is the OUTERMOST
# (first to see a request, last to see the response).
# ------------------------------------------------------------------------------

# 1. Idempotency (POST/PUT/PATCH) - innermost, closest to the routes
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(RequestContextMiddleware)

# 2. Structured request logging + request ID injection
app.add_middleware(RequestLoggingMiddleware)

# 3. Prometheus metrics counter
app.add_middleware(MetricsMiddleware)

# 4. CORS - added LAST so it is the OUTERMOST layer and also decorates
#    responses produced by the layers below (409/422/503 from idempotency)
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID", "X-Auth-Mode"],
        expose_headers=["Retry-After", "Idempotent-Replayed", "X-Request-ID"],
    )

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
    Readiness probe. The API is ready when it can serve requests:
      * PostgreSQL reachable AND the schema has been migrated
      * state Redis reachable (idempotency, locks, token blacklist)
    The cache Redis and Celery workers are reported but do NOT take the API
    out of rotation: losing the cache only slows things down, and a worker
    restart must not make the API unavailable.
    Error details are logged, never returned to the caller.
    """
    import asyncio

    import sqlalchemy

    from app.core.redis_clients import get_cache_redis, get_state_redis

    checks: dict[str, str] = {}
    healthy = True

    try:
        async with async_engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
            schema = await conn.execute(
                sqlalchemy.text("SELECT to_regclass('public.organizations')")
            )
            if schema.scalar() is None:
                checks["database"] = "schema missing: run alembic upgrade head"
                healthy = False
            else:
                checks["database"] = "ok"
    except Exception:
        logger.exception("Readiness: database check failed")
        checks["database"] = "error"
        healthy = False

    try:
        await get_state_redis().ping()
        checks["redis_state"] = "ok"
    except Exception:
        logger.exception("Readiness: state redis check failed")
        checks["redis_state"] = "error"
        healthy = False

    try:
        await get_cache_redis().ping()
        checks["redis_cache"] = "ok"
    except Exception:
        logger.warning("Readiness: cache redis unavailable (non-fatal)")
        checks["redis_cache"] = "unavailable"

    try:
        from app.core.celery_app import celery_app

        workers = await asyncio.to_thread(
            lambda: celery_app.control.inspect(timeout=1.0).ping()
        )
        checks["celery"] = "ok" if workers else "no workers"
    except Exception:
        logger.warning("Readiness: celery inspect failed (non-fatal)")
        checks["celery"] = "unavailable"

    return ORJSONResponse(
        content={"status": "ready" if healthy else "degraded", "checks": checks},
        status_code=200 if healthy else 503,
    )
