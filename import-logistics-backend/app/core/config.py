
# app/core/config.py

import secrets
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # API
    # --------------------------------------------------------------------------
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Import Profit & Logistics Intelligence System"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"          # development | staging | production
    DEBUG: bool = False

    # --------------------------------------------------------------------------
    # Security — SECRET_KEY must be set via env in production
    # --------------------------------------------------------------------------
    # Required in production. In development an empty value generates a random
    # key (tokens then stop working on restart, which is fine locally).
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24        # 24 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    ALGORITHM: str = "HS256"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        prod = self.ENVIRONMENT == "production"

        if not self.SECRET_KEY:
            if prod:
                raise ValueError("SECRET_KEY must be set in production")
            self.SECRET_KEY = secrets.token_urlsafe(64)

        if prod:
            weak = {
                "changeme",
                "change-me",
                "secret",
                "password",
                "your-secret-key",
            }

            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.lower() in weak:
                raise ValueError(
                    "SECRET_KEY must be at least 32 random characters"
                )

            if "user:password@" in self.DATABASE_URL:
                raise ValueError(
                    "DATABASE_URL still contains the default credentials"
                )

            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")

            insecure = [
                str(o)
                for o in self.BACKEND_CORS_ORIGINS
                if str(o).startswith("http://")
                and "localhost" not in str(o)
                and "127.0.0.1" not in str(o)
            ]

            if insecure:
                raise ValueError(
                    "BACKEND_CORS_ORIGINS must use https in production: "
                    f"{insecure}"
                )

        return self

    # --------------------------------------------------------------------------
    # CORS
    # --------------------------------------------------------------------------
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # --------------------------------------------------------------------------
    # Database
    # --------------------------------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+asyncpg://user:password@localhost:5432/import_logistics"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30

    # Set true when connecting through PgBouncer in transaction mode:
    # asyncpg prepared statements do not survive connection switching there.
    DATABASE_PGBOUNCER: bool = False

    # Sync URL used only by Alembic.
    # Alembic should talk to PostgreSQL directly (DDL and advisory locks do not
    # belong behind PgBouncer transaction pooling). Falls back to DATABASE_URL.
    ALEMBIC_DATABASE_URL: Optional[str] = None

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            self.ALEMBIC_DATABASE_URL or self.DATABASE_URL
        ).replace("+asyncpg", "")

    # --------------------------------------------------------------------------
    # Redis
    # --------------------------------------------------------------------------
    # REDIS_URL = durable "state" Redis: Celery broker, locks, idempotency keys,
    # token blacklist. Run it with maxmemory-policy noeviction.
    REDIS_URL: str = "redis://localhost:6379/0"

    # CACHE_REDIS_URL = disposable cache (dashboard, FX). Run it with allkeys-lru.
    # Falls back to REDIS_URL when unset (fine for local development).
    CACHE_REDIS_URL: Optional[str] = None

    # --------------------------------------------------------------------------
    # Celery
    # --------------------------------------------------------------------------
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # --------------------------------------------------------------------------
    # External APIs
    # --------------------------------------------------------------------------
    MSC_API_KEY: Optional[str] = None
    MSC_API_URL: str = "https://api.msc.com"

    EXCHANGERATE_API_KEY: Optional[str] = None
    EXCHANGERATE_API_URL: str = "https://api.exchangerate-api.com/v4/latest/"

    # Hard-coded fallback rates are only used outside production unless this is true.
    FX_ALLOW_FALLBACK: bool = False

    # Public self-registration into the default tenant. Keep false unless you
    # really want anyone to be able to create an account.
    REGISTRATION_OPEN: bool = False

    # Web clients send `X-Auth-Mode: cookie`: the refresh token then lives in
    # an httpOnly cookie (invisible to JavaScript) instead of the JSON body.
    REFRESH_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: Optional[bool] = None

    # Trust the X-Real-IP header (set by Nginx) for the audit trail. Only enable
    # when the API is reachable exclusively through your reverse proxy.
    TRUST_PROXY_HEADERS: bool = False

    # --------------------------------------------------------------------------
    # Object Storage (S3 / Cloudflare R2)
    # --------------------------------------------------------------------------
    STORAGE_BACKEND: str = "local"           # local | s3 | r2
    S3_BUCKET: Optional[str] = None
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None

    R2_ACCOUNT_ID: Optional[str] = None
    R2_BUCKET: Optional[str] = None

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024   # 10 MB

    ALLOWED_MIME_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    ]

    # --------------------------------------------------------------------------
    # Email
    # --------------------------------------------------------------------------
    EMAIL_ENABLED: bool = False
    EMAIL_PROVIDER: str = "smtp"             # smtp | sendgrid | mailgun
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    SENDGRID_API_KEY: Optional[str] = None
    MAILGUN_API_KEY: Optional[str] = None
    MAILGUN_DOMAIN: Optional[str] = None

    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: str = "Import Logistics"

    @field_validator("EMAILS_FROM_EMAIL", mode="before")
    @classmethod
    def empty_email_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    # --------------------------------------------------------------------------
    # First superuser (used only by init script, never at runtime)
    # --------------------------------------------------------------------------
    FIRST_SUPERUSER_EMAIL: Optional[EmailStr] = None
    FIRST_SUPERUSER_USERNAME: Optional[str] = None
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None

    # --------------------------------------------------------------------------
    # Pagination
    # --------------------------------------------------------------------------
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # --------------------------------------------------------------------------
    # Pricing
    # --------------------------------------------------------------------------
    DEFAULT_PROFIT_MARGIN: float = 0.20
    PRICING_MIN_MARGIN: float = 0.05
    PRICING_HALF_LIFE_DAYS: float = 30.0
    PRICING_MAX_COMP_AGE_DAYS: int = 180

    MIN_PROFIT_MARGIN: float = 0.05
    MAX_PROFIT_MARGIN: float = 1.0

    SCRAPING_ENABLED: bool = True

    SCRAPING_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # --------------------------------------------------------------------------
    # Tracking
    # --------------------------------------------------------------------------
    TRACKING_CHECK_INTERVAL: int = 3600      # seconds

    # --------------------------------------------------------------------------
    # Rate Limiting
    # --------------------------------------------------------------------------
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_API: str = "100/minute"
    RATE_LIMIT_TRACKING: str = "20/minute"

    # --------------------------------------------------------------------------
    # Account Lockout
    # --------------------------------------------------------------------------
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # --------------------------------------------------------------------------
    # Monitoring
    # --------------------------------------------------------------------------
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None

    # --------------------------------------------------------------------------
    # Idempotency
    # --------------------------------------------------------------------------
    IDEMPOTENCY_KEY_TTL: int = 86400
    # postgres = durable source of truth (default); redis = faster but can lose
    # keys on flush/restart.
    IDEMPOTENCY_BACKEND: str = "postgres"
    IDEMPOTENCY_LOCK_TTL: int = 120
    IDEMPOTENCY_MAX_BODY: int = 12 * 1024 * 1024

    # If Redis is down: True = reject the request (503), False = run it unprotected.
    IDEMPOTENCY_FAIL_CLOSED: bool = True

    # --------------------------------------------------------------------------
    # Elasticsearch (optional, falls back to PostgreSQL FTS)
    # --------------------------------------------------------------------------
    ELASTICSEARCH_URL: Optional[str] = None


settings = Settings()


# ==============================================================================
# Constants (not env-driven)
# ==============================================================================
SUPPORTED_CURRENCIES = ["USD", "EUR", "CZK", "NGN"]
BASE_CURRENCY = "USD"

CONTAINER_TYPES = ["20ft", "40ft"]
ITEM_CONDITIONS = ["new", "tokunbo", "used"]

ITEM_CATEGORIES = [
    "electronics",
    "vehicles",
    "engines",
    "appliances",
    "food_items",
    "laptops",
    "other",
]

USER_ROLES = ["admin", "manager", "clerk", "viewer"]
ALLOCATION_METHODS = ["weight_based", "value_based"]

EXPENSE_TYPES = [
    "loading_fee",
    "shipping_fee",
    "clearing_fee",
    "offloading_fee",
    "warehouse_fee",
    "security_fee",
    "extra_fee",
]

PRICING_SOURCES = {
    "jiji": "https://jiji.ng",
    "ebay": "https://ebay.com",
    "mobile_de": "https://mobile.de",
    "autoscout24": "https://autoscout24.com",
    "bazos_cz": "https://bazos.cz",
}

TRACKING_STATUSES = [
    "booked",
    "gate_in",
    "loaded",
    "departed",
    "in_transit",
    "arrived",
    "discharged",
    "gate_out",
    "delivered",
]

CELERY_QUEUES = [
    "tracking_queue",
    "scraping_queue",
    "pricing_queue",
    "fx_queue",
    "notification_queue",
]
