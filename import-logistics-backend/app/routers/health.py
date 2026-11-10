
# app/routers/health.py
# NOTE: /health and /ready are also mounted directly on app in main.py
# (outside the rate limiter). This router provides versioned equivalents
# under /api/v1/health for internal service-to-service checks.

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

router = APIRouter()


@router.get("/live", include_in_schema=False)
async def liveness():
    return {"status": "ok"}


@router.get("/ready", include_in_schema=False)
async def readiness():
    from app.core.database import async_engine
    from app.core.config import settings

    import redis.asyncio as aioredis
    import sqlalchemy

    checks: dict[str, str] = {}
    healthy = True

    # Database health check
    try:
        async with async_engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))

        checks["database"] = "ok"

    except Exception:
        checks["database"] = "error"
        healthy = False

    # Redis health check
    r = None

    try:
        # redis-py 4.6.0: from_url() returns the client directly.
        r = aioredis.from_url(settings.REDIS_URL)

        await r.ping()
        checks["redis"] = "ok"

    except Exception:
        checks["redis"] = "error"
        healthy = False

    finally:
        if r is not None:
            try:
                await r.close()
            except Exception:
                checks["redis"] = "error"
                healthy = False

    return ORJSONResponse(
        content={
            "status": "ready" if healthy else "degraded",
            "checks": checks,
        },
        status_code=200 if healthy else 503,
    )
