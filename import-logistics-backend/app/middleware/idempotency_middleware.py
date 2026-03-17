# app/middleware/idempotency_middleware.py
"""
Idempotency middleware for mutating endpoints.

Mobile clients often retry requests on network failure.
This middleware stores the first response for a given
Idempotency-Key and replays it on duplicate requests.

Usage (client side):
    POST /api/v1/containers/
    Idempotency-Key: <uuid>

Scope:
    Only POST requests with an Idempotency-Key header are checked.
    Safe methods (GET, HEAD) and other methods are passed through.

Storage:
    Redis key: idempotency:{user_id}:{idempotency_key}
    TTL:       settings.IDEMPOTENCY_KEY_TTL (default 24 h)
"""
import json
import logging
from typing import Callable

import redis.asyncio as aioredis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

_IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH"}


class IdempotencyMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to mutating methods
        if request.method not in _IDEMPOTENT_METHODS:
            return await call_next(request)

        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return await call_next(request)

        # Extract user identity for key namespacing
        user_id = getattr(getattr(request, "state", None), "user_id", "anon")
        redis_key = f"idempotency:{user_id}:{idem_key}"

        r = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            cached = await r.get(redis_key)
            if cached:
                logger.info("Idempotency cache hit: %s", redis_key)
                data = json.loads(cached)
                return JSONResponse(
                    content=data["body"],
                    status_code=data["status_code"],
                    headers={"X-Idempotency-Replayed": "true"},
                )

            # Execute the real request
            response = await call_next(request)

            # Cache only successful responses (2xx)
            if 200 <= response.status_code < 300:
                # Read and buffer the response body
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk

                try:
                    body = json.loads(body_bytes)
                    payload = json.dumps({
                        "status_code": response.status_code,
                        "body":        body,
                    })
                    await r.setex(redis_key, settings.IDEMPOTENCY_KEY_TTL, payload)
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning("Could not cache idempotency response: %s", e)

                return Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            return response

        finally:
            await r.aclose()