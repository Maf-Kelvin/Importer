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
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24        # 24 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    ALGORITHM: str = "HS256"

    @model_validator(mode="after")
    def enforce_secret_key_in_prod(self) -> "Settings":
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == "":
            raise ValueError("SECRET_KEY must be set in production environment")
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
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/import_logistics"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30

    # Sync URL used only by Alembic
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    # --------------------------------------------------------------------------
    # Redis
    # --------------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

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
        "image/jpeg", "image/png", "image/webp", "application/pdf"
    ]

    # --------------------------------------------------------------------------
    # Email
    # --------------------------------------------------------------------------
    EMAIL_ENABLED: bool = False
    EMAIL_PROVIDER: str = "smtp"             # smtp | sendgrid | mailgun | ses
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
    IDEMPOTENCY_KEY_TTL: int = 86400         # 24 hours in seconds

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
    "electronics", "vehicles", "engines",
    "appliances", "food_items", "laptops", "other",
]
USER_ROLES = ["admin", "manager", "clerk", "viewer"]
ALLOCATION_METHODS = ["weight_based", "value_based"]

EXPENSE_TYPES = [
    "loading_fee", "shipping_fee", "clearing_fee",
    "offloading_fee", "warehouse_fee", "security_fee", "extra_fee",
]

PRICING_SOURCES = {
    "jiji":        "https://jiji.ng",
    "ebay":        "https://ebay.com",
    "mobile_de":   "https://mobile.de",
    "autoscout24": "https://autoscout24.com",
    "bazos_cz":    "https://bazos.cz",
}

TRACKING_STATUSES = [
    "booked", "gate_in", "loaded", "departed",
    "in_transit", "arrived", "discharged", "gate_out", "delivered",
]

CELERY_QUEUES = [
    "tracking_queue", "scraping_queue",
    "pricing_queue", "fx_queue", "notification_queue",
]