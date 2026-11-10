# alembic/env.py
"""Alembic environment.

Migrations run over a plain SYNCHRONOUS connection (psycopg2) straight to PostgreSQL:
  * DDL and advisory locks do not belong behind PgBouncer transaction pooling, so
    ALEMBIC_DATABASE_URL (a direct URL) is preferred; DATABASE_URL is the fallback.
  * The previous version set a sync URL but then built an ASYNC engine from it, which fails
    with "The asyncio extension requires an async driver", so `alembic upgrade head` could never run.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import ALL models so every table is registered on Base.metadata (app/models/__init__.py imports them all)
from app.core.config import settings
from app.models import Base  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL without a live database connection (alembic upgrade head --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,          # no pooling in a migration run
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
