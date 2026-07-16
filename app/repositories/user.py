"""Persistence access for the User entity.

Repository responsibilities (only):
- translate intent ("find user by email", "create user") into SQLAlchemy queries
- operate on the AsyncSession it is given; never open or commit transactions

The caller (service) owns the transaction boundary. ``create`` flushes so the
generated primary key is populated, but does NOT commit -- that keeps the row
part of the caller's larger unit of work.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        """Return the user with this email, or ``None`` if absent."""
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, *, email: str, hashed_password: str,
                     full_name: str | None) -> User:
        """Add a new user and flush so ``user.id`` is available. No commit."""
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
        )
        self._session.add(user)
        # flush() sends the INSERT so the DB assigns user.id (needed to link the
        # membership row) and surfaces constraint violations here -- but it does
        # NOT commit. The service owns the commit, so this write stays part of
        # its single transaction and unwinds with it on any later failure.
        await self._session.flush()
        return user
