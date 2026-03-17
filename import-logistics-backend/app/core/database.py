# app/core/database.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ------------------------------------------------------------------------------
# Async engine — used by FastAPI and services
# ------------------------------------------------------------------------------
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_pre_ping=True,       # verify connection health before use
    echo=settings.DEBUG,      # SQL logging in debug mode only
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,   # objects remain usable after commit
    autocommit=False,
    autoflush=False,
)

# ------------------------------------------------------------------------------
# FastAPI dependency — yields a session per request
# ------------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ------------------------------------------------------------------------------
# Transaction helper — wraps a unit of work in a single atomic transaction.
# Usage:
#   async with transaction(db):
#       db.add(obj)
# ------------------------------------------------------------------------------
@asynccontextmanager
async def transaction(session: AsyncSession):
    async with session.begin():
        yield session


# ------------------------------------------------------------------------------
# Sync engine — used ONLY by Alembic migrations (not by FastAPI)
# ------------------------------------------------------------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)