# app/middleware/idempotency_middleware.py
"""
Idempotency middleware (pure ASGI) for POST / PUT / PATCH.

Client usage:
    POST /api/v1/containers/
    Authorization: Bearer <access token>
    Idempotency-Key: 3f2b8c1e-0a4d-4e7a-9d55-1b2c3d4e5f60

Behaviour (see app/core/idempotency.py for the state machine):
    first request            -> runs normally, 2xx response is stored
    same key, same request   -> stored response replayed (Idempotent-Replayed: true)
    same key, other request  -> 422
    same key, still running  -> 409 + Retry-After
    request failed (non-2xx) -> key released, client may retry
    no / invalid access token-> idempotency skipped (the endpoint will 401 anyway)

Keys are namespaced by tenant + user taken from the *verified* JWT, so one
user can never read another user's stored response.

Pure ASGI (not BaseHTTPMiddleware) so the request body can be read for
fingerprinting and then handed to the application unchanged.
"""
import logging
from typing import Optional

from jose import JWTError
from starlette.datastructures import Headers
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import security
from app.core.config import settings
from app.core.idempotency import (
    IdempotencyStore,
    PostgresIdempotencyStore,
    RedisIdempotencyStore,
    decode_response,
    encode_response,
    fingerprint,
    new_owner,
    storage_key,
    validate_key,
)
from app.core.redis_clients import get_state_redis

logger = logging.getLogger(__name__)

_METHODS = {"POST", "PUT", "PATCH"}
_MAX_STORED_RESPONSE = 1024 * 1024  # do not store responses bigger than 1 MB


class IdempotencyMiddleware:
    def __init__(self, app: ASGIApp, store: Optional[IdempotencyStore] = None) -> None:
        self.app = app
        self._store = store

    @property
    def store(self) -> IdempotencyStore:
        if self._store is None:
            if settings.IDEMPOTENCY_BACKEND == "redis":
                self._store = RedisIdempotencyStore(get_state_redis)
            else:
                from app.core.database import AsyncSessionLocal
                self._store = PostgresIdempotencyStore(AsyncSessionLocal)
        return self._store

    # --------------------------------------------------------------------------
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _METHODS:
            return await self.app(scope, receive, send)

        headers = Headers(scope=scope)
        raw_key = headers.get("idempotency-key")
        if not raw_key:
            return await self.app(scope, receive, send)

        identity = self._identity(headers.get("authorization"))
        if identity is None:
            return await self.app(scope, receive, send)

        try:
            key = validate_key(raw_key)
        except ValueError as exc:
            return await JSONResponse({"detail": str(exc)}, status_code=400)(scope, receive, send)

        body = await self._read_body(receive)
        if body is None:  # client disconnected
            return
        if len(body) > settings.IDEMPOTENCY_MAX_BODY:
            return await self.app(scope, self._replay(body, receive), send)

        fp = fingerprint(
            scope["method"], scope["path"], scope.get("query_string", b"").decode(), body
        )
        skey = storage_key(identity, key)
        owner = new_owner()

        try:
            outcome = await self.store.claim(skey, fp, owner, settings.IDEMPOTENCY_LOCK_TTL)
        except Exception as exc:
            logger.error("Idempotency store unavailable: %s", exc)
            if settings.IDEMPOTENCY_FAIL_CLOSED:
                return await JSONResponse(
                    {"detail": "Idempotency service unavailable, please retry"},
                    status_code=503,
                    headers={"Retry-After": "5"},
                )(scope, receive, send)
            return await self.app(scope, self._replay(body, receive), send)

        if outcome.status == "replay":
            status, content_type, content = decode_response(outcome.record)
            response = Response(
                content=content,
                status_code=status,
                headers={"Idempotent-Replayed": "true"},
                media_type=content_type,
            )
            return await response(scope, receive, send)
        if outcome.status == "in_progress":
            return await JSONResponse(
                {"detail": "A request with this Idempotency-Key is still being processed"},
                status_code=409,
                headers={"Retry-After": "1"},
            )(scope, receive, send)
        if outcome.status == "mismatch":
            return await JSONResponse(
                {"detail": "Idempotency-Key was already used with a different request"},
                status_code=422,
            )(scope, receive, send)

        # ---- claimed: run the endpoint and capture its response -----------------
        captured = {"status": None, "content_type": None, "chunks": [], "size": 0}

        async def capture(message: Message) -> None:
            if message["type"] == "http.response.start":
                captured["status"] = message["status"]
                for name, value in message.get("headers", []):
                    if name.lower() == b"content-type":
                        captured["content_type"] = value.decode("latin-1")
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                captured["size"] += len(chunk)
                if captured["size"] <= _MAX_STORED_RESPONSE:
                    captured["chunks"].append(chunk)
            await send(message)

        try:
            await self.app(scope, self._replay(body, receive), capture)
        except BaseException:
            await self._safe_release(skey, owner)
            raise

        status = captured["status"]
        storable = (
            status is not None
            and 200 <= status < 300
            and captured["size"] <= _MAX_STORED_RESPONSE
        )
        if storable:
            try:
                await self.store.complete(
                    skey, fp, owner,
                    encode_response(status, captured["content_type"], b"".join(captured["chunks"])),
                    settings.IDEMPOTENCY_KEY_TTL,
                )
            except Exception as exc:
                logger.error("Could not store idempotent response: %s", exc)
        else:
            await self._safe_release(skey, owner)

    # --------------------------------------------------------------------------
    async def _safe_release(self, skey: str, owner: str) -> None:
        try:
            await self.store.release(skey, owner)
        except Exception as exc:
            logger.error("Could not release idempotency key: %s", exc)

    @staticmethod
    def _identity(authorization: Optional[str]) -> Optional[str]:
        """tenant:user from a verified access token, or None."""
        if not authorization or not authorization.lower().startswith("bearer "):
            return None
        try:
            payload = security.decode_token(authorization[7:].strip())
        except JWTError:
            return None
        if not security.verify_token_type(payload, security.ACCESS_TOKEN_TYPE):
            return None
        sub, tenant = payload.get("sub"), payload.get("tenant_id")
        if not sub or tenant is None:
            return None
        return f"{tenant}:{sub}"

    @staticmethod
    async def _read_body(receive: Receive) -> Optional[bytes]:
        chunks = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return None
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                return b"".join(chunks)

    @staticmethod
    def _replay(body: bytes, receive: Receive) -> Receive:
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        return replay
