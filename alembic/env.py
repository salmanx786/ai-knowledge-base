import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.config.settings import settings
from app.db.base import Base

# Import models so their tables register on Base.metadata for autogenerate.
# Add new model modules here as they are created.
from app.models import document  # noqa: F401
from app.models import organization  # noqa: F401
from app.models import organization_member  # noqa: F401
from app.models import user  # noqa: F401

# Alembic Config object, provides access to values within alembic.ini.
config = context.config

# Inject the database URL from application settings (single source of truth).
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up loggers from the ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata used as the autogenerate target.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through a sync-adapted connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
