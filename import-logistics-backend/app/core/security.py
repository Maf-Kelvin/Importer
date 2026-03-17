# app/core/security.py
from datetime import datetime, timedelta, UTC
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM         = settings.ALGORITHM
ACCESS_TOKEN_TYPE  = "access"
REFRESH_TOKEN_TYPE = "refresh"


# ------------------------------------------------------------------------------
# Password
# ------------------------------------------------------------------------------
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ------------------------------------------------------------------------------
# Access token
# ------------------------------------------------------------------------------
def create_access_token(
    subject: str,
    tenant_id: int,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub":       subject,
        "tenant_id": tenant_id,
        "role":      role,
        "type":      ACCESS_TOKEN_TYPE,
        "exp":       expire,
        "iat":       datetime.now(UTC),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


# ------------------------------------------------------------------------------
# Refresh token
# ------------------------------------------------------------------------------
def create_refresh_token(
    subject: str,
    tenant_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub":       subject,
        "tenant_id": tenant_id,
        "type":      REFRESH_TOKEN_TYPE,
        "exp":       expire,
        "iat":       datetime.now(UTC),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


# ------------------------------------------------------------------------------
# Token decoding — returns payload dict or raises JWTError
# ------------------------------------------------------------------------------
def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise


def verify_token_type(payload: dict, expected_type: str) -> bool:
    return payload.get("type") == expected_type


# ------------------------------------------------------------------------------
# Token blacklist — Redis backed
# blacklisted tokens are stored until their natural expiry so we never
# need a background cleanup job.
# ------------------------------------------------------------------------------
import redis.asyncio as aioredis


async def _get_redis() -> aioredis.Redis:
    return await aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def blacklist_token(token: str, expires_in_seconds: int) -> None:
    """Add token to blacklist. Key expires automatically."""
    r = await _get_redis()
    await r.setex(f"bl:{token}", expires_in_seconds, "1")
    await r.aclose()


async def is_token_blacklisted(token: str) -> bool:
    r = await _get_redis()
    result = await r.exists(f"bl:{token}")
    await r.aclose()
    return bool(result)


# ------------------------------------------------------------------------------
# Account lockout helpers — Redis backed
# ------------------------------------------------------------------------------
async def record_failed_login(username: str) -> int:
    """Increment failed login counter. Returns current count."""
    r = await _get_redis()
    key = f"login_fail:{username}"
    count = await r.incr(key)
    # Set expiry only on first failure so the window resets correctly
    if count == 1:
        await r.expire(key, settings.LOCKOUT_DURATION_MINUTES * 60)
    await r.aclose()
    return int(count)


async def clear_failed_logins(username: str) -> None:
    r = await _get_redis()
    await r.delete(f"login_fail:{username}")
    await r.aclose()


async def is_account_locked(username: str) -> bool:
    r = await _get_redis()
    key   = f"login_fail:{username}"
    count = await r.get(key)
    await r.aclose()
    return int(count or 0) >= settings.MAX_LOGIN_ATTEMPTS