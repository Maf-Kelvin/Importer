# app/utils/audit.py
"""Pure helpers for audit logging (standard library only)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Mapping

SENSITIVE_KEYS = frozenset(
    {"password", "hashed_password", "token", "access_token", "refresh_token",
     "secret", "api_key", "authorization"}
)
REDACTED = "[redacted]"


def to_jsonable(value: Any) -> Any:
    """Make a value safe to store in a JSON column (Decimal -> exact string)."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return to_jsonable(value.value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def snapshot(obj: Any, fields: Iterable[str]) -> dict[str, Any]:
    """Read the listed attributes from an object as JSON-safe values."""
    return {f: to_jsonable(getattr(obj, f, None)) for f in fields}


def diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Only the keys whose value changed: {key: {"from": old, "to": new}}."""
    changes: dict[str, dict[str, Any]] = {}
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old != new:
            changes[key] = {"from": old, "to": new}
    return changes


def redact(data: Any) -> Any:
    """Mask sensitive keys anywhere inside nested dicts/lists."""
    if isinstance(data, Mapping):
        return {
            k: (REDACTED if str(k).lower() in SENSITIVE_KEYS else redact(v))
            for k, v in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [redact(v) for v in data]
    return data
