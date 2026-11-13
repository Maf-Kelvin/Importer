# app/core/token_claims.py
"""Rules for binding a JWT to the user it was issued to.

A token carries three identity claims:
  sub        the user's numeric id (not the username, which an account can change)
  tenant_id  the organisation
  pwf        a short fingerprint of the user's current password hash

Because `pwf` is derived from the stored hash, changing the password makes every
older access and refresh token stop matching, so sessions end without needing a
database column or a revocation list. No imports beyond the standard library, so
this is cheap to test.
"""
import hashlib
import hmac
from typing import Any, Mapping


def password_fingerprint(hashed_password: str) -> str:
    return hashlib.sha256(("pwf:" + hashed_password).encode()).hexdigest()[:16]


def parse_subject(payload: Mapping[str, Any]) -> int | None:
    """The user id in `sub`, or None when it is missing or not a number."""
    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def claims_match_user(payload: Mapping[str, Any], user: Any) -> bool:
    """True only if the token was issued to this user, in this tenant, for this password."""
    if parse_subject(payload) != user.id:
        return False
    if payload.get("tenant_id") != user.tenant_id:
        return False
    pwf = payload.get("pwf")
    if not isinstance(pwf, str):
        return False
    return hmac.compare_digest(pwf, password_fingerprint(user.hashed_password))