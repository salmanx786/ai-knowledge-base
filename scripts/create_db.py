"""Create all tables directly from SQLAlchemy models (SQLite-friendly alternative to alembic)."""
import asyncio
from app.db.engine import engine
from app.db.base import Base
from app.models import chunk, document, organization, organization_member, user  # noqa: F401


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created.")


asyncio.run(main())
