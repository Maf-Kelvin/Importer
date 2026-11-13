import logging
import logging.config
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_client import make_asgi_app
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import settings
from app.core.database import async_engine
from app.core.redis_clients import close_redis_clients
from app.middleware.request_context_middleware import RequestContextMiddleware
from app.services.fx_service import FXRateUnavailable
from app.middleware.logging_middleware import (
    RequestLoggingMiddleware,
    MetricsMiddleware,
)
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
            "class": "logging.StreamHandler",
            "formatter": (
                "json"
                if settings.ENVIRONMENT == "production"
                else "standard"
            ),
        },
    },
    "root": {
        "level": settings.LOG_LEVEL,
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
        traces_sample_rate=0.2,
        send_default_pii=False,
    )
    logger.info("Sentry initialised (env=%s)", settings.ENVIRONMENT)


# ------------------------------------------------------------------------------
# OpenTelemetry — only when endpoint is configured
# ------------------------------------------------------------------------------
def _setup_otel() -> None:
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT
            )
        )
    )

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(
        engine=async_engine.sync_engine
    )

    logger.info("OpenTelemetry tracing enabled")


# ------------------------------------------------------------------------------
# Lifespan — startup + shutdown hooks
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(
        "Starting %s (env=%s)",
        settings.PROJECT_NAME,
        settings.ENVIRONMENT,
    )

    # Verify DB connectivity
    try:
        import sqlalchemy

        async with async_engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))

        logger.info("Database connection OK")

    except Exception as e:
        logger.critical("Database connection failed: %s", e)
        raise

    # Verify Redis connectivity
    try:
        import redis.asyncio as aioredis

        # redis-py 4.6.0: from_url() returns the client directly.
        r = aioredis.from_url(settings.REDIS_URL)

        await r.ping()
        await r.close()

        logger.info("Redis connection OK")

    except Exception as e:
        logger.critical("Redis connection failed: %s", e)
        raise

    _setup_otel()

    yield

    # Shutdown
    logger.info(
        "Shutting down — closing Redis and disposing DB engine"
    )

    await close_redis_clients()
    await async_engine.dispose()


# ------------------------------------------------------------------------------
# App instance
# NOTE: create_all is intentionally absent — use `alembic upgrade head`
# ------------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=(
        f"{settings.API_V1_STR}/openapi.json"
        if settings.ENVIRONMENT != "production"
        else None
    ),
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)


# Rate limiting is done by nginx (docker/nginx/nginx.conf), not in the app.


@app.exception_handler(FXRateUnavailable)
async def fx_unavailable_handler(
    request: Request,
    exc: FXRateUnavailable,
):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Exchange rate service unavailable, please retry later"
            )
        },
        headers={"Retry-After": "30"},
    )


# ------------------------------------------------------------------------------
# Middleware
# Starlette wraps middleware in reverse order:
# the last middleware added is the outermost.
# ------------------------------------------------------------------------------

app.add_middleware(IdempotencyMiddleware)
app.add_middleware(RequestContextMiddleware)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MetricsMiddleware)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin)
            for origin in settings.BACKEND_CORS_ORIGINS
        ],
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "X-Request-ID",
            "X-Auth-Mode",
        ],
        expose_headers=[
            "Retry-After",
            "Idempotent-Replayed",
            "X-Request-ID",
        ],
    )


# ------------------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------------------
app.include_router(
    api_router,
    prefix=settings.API_V1_STR,
)


# ------------------------------------------------------------------------------
# Prometheus metrics endpoint
# ------------------------------------------------------------------------------
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ------------------------------------------------------------------------------
# Health endpoints
# ------------------------------------------------------------------------------
@app.get(
    "/health",
    tags=["health"],
    include_in_schema=False,
)
async def liveness():
    """Kubernetes liveness probe."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
    }


@app.get(
    "/ready",
    tags=["health"],
    include_in_schema=False,
)
async def readiness():
    """
    Readiness probe.

    PostgreSQL and state Redis are required.
    Cache Redis and Celery workers are non-fatal.
    """
    import asyncio
    import sqlalchemy

    from app.core.redis_clients import (
        get_cache_redis,
        get_state_redis,
    )

    checks: dict[str, str] = {}
    healthy = True

    # PostgreSQL
    try:
        async with async_engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))

            schema = await conn.execute(
                sqlalchemy.text(
                    "SELECT to_regclass('public.organizations')"
                )
            )

            if schema.scalar() is None:
                checks["database"] = (
                    "schema missing: run alembic upgrade head"
                )
                healthy = False
            else:
                checks["database"] = "ok"

    except Exception:
        logger.exception(
            "Readiness: database check failed"
        )
        checks["database"] = "error"
        healthy = False

    # State Redis
    try:
        await get_state_redis().ping()
        checks["redis_state"] = "ok"

    except Exception:
        logger.exception(
            "Readiness: state redis check failed"
        )
        checks["redis_state"] = "error"
        healthy = False

    # Cache Redis
    try:
        await get_cache_redis().ping()
        checks["redis_cache"] = "ok"

    except Exception:
        logger.warning(
            "Readiness: cache Redis unavailable (non-fatal)"
        )
        checks["redis_cache"] = "unavailable"

    # Celery workers
    try:
        from app.core.celery_app import celery_app

        workers = await asyncio.to_thread(
            lambda: celery_app.control.inspect(
                timeout=1.0
            ).ping()
        )

        checks["celery"] = (
            "ok" if workers else "no workers"
        )

    except Exception:
        logger.warning(
            "Readiness: Celery inspect failed (non-fatal)"
        )
        checks["celery"] = "unavailable"

    return ORJSONResponse(
        content={
            "status": (
                "ready" if healthy else "degraded"
            ),
            "checks": checks,
        },
        status_code=200 if healthy else 503,
    )