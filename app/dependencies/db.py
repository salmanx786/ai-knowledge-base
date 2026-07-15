from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped async DB session.

    The `async with` block guarantees the session is closed (and its
    connection returned to the pool) when the request finishes.
    """
    async with SessionFactory() as session:
        yield session
