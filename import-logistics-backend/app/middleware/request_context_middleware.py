# app/middleware/request_context_middleware.py
"""Stores client IP and user agent in context variables for audit logging.

X-Real-IP is only trusted when TRUST_PROXY_HEADERS=true (set it when the API
sits behind Nginx, which overwrites that header). Otherwise a client could
forge its own address in the audit trail.
"""
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core import request_context
from app.core.config import settings


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        ip = None
        if settings.TRUST_PROXY_HEADERS:
            ip = headers.get("x-real-ip")
        if not ip and scope.get("client"):
            ip = scope["client"][0]
        ua = headers.get("user-agent")
        ip_token = request_context.client_ip.set(ip[:45] if ip else None)
        ua_token = request_context.user_agent.set(ua[:512] if ua else None)
        try:
            await self.app(scope, receive, send)
        finally:
            request_context.client_ip.reset(ip_token)
            request_context.user_agent.reset(ua_token)
