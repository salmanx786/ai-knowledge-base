from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config.settings import settings

# Single async engine for the whole application (a connection pool lives here).
# `echo` follows the debug flag so we don't log every statement in production.
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)
