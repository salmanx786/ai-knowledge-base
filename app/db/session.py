from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.engine import engine

# Factory for request-scoped AsyncSession instances.
# `expire_on_commit=False` keeps attributes usable after commit, which is the
# common convention for async web handlers.
SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)
