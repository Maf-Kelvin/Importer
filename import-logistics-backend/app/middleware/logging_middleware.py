# app/middleware/logging_middleware.py
import json
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured JSON access log for every request.

    Log fields:
        request_id  — UUID injected into request state and response header
        method      — HTTP method
        path        — URL path
        status_code — response status
        latency_ms  — wall-clock time in milliseconds
        user_id     — extracted from JWT sub claim if present (no DB call)
        tenant_id   — extracted from JWT tenant_id claim if present
        ip          — client IP (respects X-Forwarded-For behind Nginx)
        user_agent  — client user-agent string
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract lightweight identity from JWT without a full DB round-trip
        user_id   = None
        tenant_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from jose import jwt as _jwt
                from app.core.config import settings
                payload = _jwt.decode(
                    auth_header[7:],
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM],
                    options={"verify_exp": False},   # already verified in deps
                )
                user_id   = payload.get("sub")
                tenant_id = payload.get("tenant_id")
            except Exception:
                pass  # token invalid — auth layer will handle it

        start = time.perf_counter()

        response: Response = await call_next(request)

        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        # Inject request ID into response so clients can correlate logs
        response.headers["X-Request-ID"] = request_id

        log_record = {
            "request_id": request_id,
            "method":     request.method,
            "path":       request.url.path,
            "query":      str(request.url.query) or None,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "user_id":    user_id,
            "tenant_id":  tenant_id,
            "ip":         _get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
        }

        level = logging.WARNING if response.status_code >= 500 else logging.INFO
        logger.log(level, json.dumps(log_record))

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Increments Prometheus counters per request.
    Kept separate from logging so each concern is independently testable.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        from prometheus_client import Counter, Histogram

        REQUEST_COUNT = Counter(
            "http_requests_total",
            "Total HTTP request count",
            ["method", "path", "status"],
        )
        REQUEST_LATENCY = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "path"],
        )

        start = time.perf_counter()
        response = await call_next(request)
        latency  = time.perf_counter() - start

        path = request.url.path
        REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path).observe(latency)

        return response


def _get_client_ip(request: Request) -> str | None:
    """Respects X-Forwarded-For set by Nginx."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None