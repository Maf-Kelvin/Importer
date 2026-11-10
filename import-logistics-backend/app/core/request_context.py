# app/core/request_context.py
"""Per-request values (client IP, user agent) visible to services without
passing the HTTP request through every function. Set by RequestContextMiddleware."""
from contextvars import ContextVar
from typing import Optional

client_ip: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
user_agent: ContextVar[Optional[str]] = ContextVar("user_agent", default=None)
