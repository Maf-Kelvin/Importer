from typing import List, Optional, Union
from pydantic import BaseSettings, AnyHttpUrl, validator
import os


class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-super-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Server
    SERVER_NAME: str = "Import Logistics API"
    SERVER_HOST: AnyHttpUrl = "http://localhost"
    PROJECT_NAME: str = "Import Profit & Logistics Intelligence System"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/import_logistics"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # External APIs
    MSC_API_KEY: Optional[str] = None
    MSC_API_URL: str = "https://api.msc.com"
    
    # FX API
    EXCHANGERATE_API_KEY: Optional[str] = None
    EXCHANGERATE_API_URL: str = "https://api.exchangerate-api.com/v4/latest/"
    
    # Scraping Configuration
    SCRAPING_ENABLED: bool = True
    SCRAPING_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Notification Settings
    EMAIL_ENABLED: bool = False
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # First superuser
    FIRST_SUPERUSER: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "changethis"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000
    
    # File uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Pricing configuration
    DEFAULT_PROFIT_MARGIN: float = 0.20  # 20%
    MIN_PROFIT_MARGIN: float = 0.05  # 5%
    MAX_PROFIT_MARGIN: float = 1.0   # 100%
    
    # Tracking notifications
    TRACKING_CHECK_INTERVAL: int = 3600  # 1 hour in seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


# Currency configuration
SUPPORTED_CURRENCIES = ["USD", "EUR", "CZK", "NGN"]
BASE_CURRENCY = "USD"

# Container types
CONTAINER_TYPES = ["20ft", "40ft"]

# Item conditions
ITEM_CONDITIONS = ["new", "tokunbo", "used"]

# Item categories
ITEM_CATEGORIES = [
    "electronics",
    "vehicles", 
    "engines",
    "appliances",
    "food_items",
    "laptops",
    "other"
]

# User roles
USER_ROLES = ["admin", "manager", "clerk", "viewer"]

# Cost allocation methods
ALLOCATION_METHODS = ["weight_based", "value_based"]

# Expense types
EXPENSE_TYPES = [
    "loading_fee",
    "shipping_fee", 
    "clearing_fee",
    "offloading_fee",
    "warehouse_fee",
    "security_fee",
    "extra_fee"
]

# Pricing sources
PRICING_SOURCES = {
    "jiji": "https://jiji.ng",
    "ebay": "https://ebay.com", 
    "mobile_de": "https://mobile.de",
    "autoscout24": "https://autoscout24.com",
    "bazos_cz": "https://bazos.cz"
}

# MSC tracking statuses
TRACKING_STATUSES = [
    "booked",
    "gate_in",
    "loaded",
    "departed", 
    "in_transit",
    "arrived",
    "discharged",
    "gate_out",
    "delivered"
]