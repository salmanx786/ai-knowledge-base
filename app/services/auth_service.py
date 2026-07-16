"""Authentication domain logic: registration and login.

Service responsibilities:
- orchestrate repositories and password hashing into a use case
- own the transaction boundary via ``async with session.begin()`` (commits on
  clean exit, rolls back on any exception -- no manual commit/rollback)
- translate domain rules ("email must be unique", "credentials must match")
  into domain errors

The service holds the AsyncSession and the repositories bound to it, so every
operation in a single service call shares one unit of work.
"""

from app.core.security import hash_password, verify_password
from app.models.organization_member import MembershipStatus, OrganizationRole
from app.models.user import User
from app.repositories.errors import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from app.repositories.organization import OrganizationRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class AuthenticationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._orgs = OrganizationRepository(session)

    async def register_user(self, data: RegisterRequest) -> User:
        """Create a user, their initial organization, and an OWNER membership.

        All three rows are written inside a single transaction: either the
        whole tenant bootstrap succeeds, or nothing is persisted.
        """
        try:
            # `session.begin()` is SQLAlchemy 2.0's preferred boundary: it
            # commits on clean exit and rolls back on any exception, so the
            # service no longer calls commit()/rollback() by hand.
            async with self._session.begin():
                # Pre-check runs *inside* the transaction. It's a UX shortcut
                # that turns the common duplicate case into a clean domain
                # error; the DB unique index remains the real guarantee (see
                # the IntegrityError handler below for the concurrent race).
                existing = await self._users.get_by_email(data.email)
                if existing is not None:
                    raise EmailAlreadyExistsError(data.email)

                user = await self._users.create(
                    email=data.email,
                    hashed_password=hash_password(data.password),
                    full_name=data.full_name,
                )
                organization = await self._orgs.create(
                    name=data.organization_name
                )
                await self._orgs.add_member(
                    organization_id=organization.id,
                    user_id=user.id,
                    role=OrganizationRole.OWNER,
                    status=MembershipStatus.ACTIVE,
                )
        except IntegrityError as exc:
            # Two concurrent registrations can both pass the pre-check, then
            # one trips the users.email unique index on flush/commit. The
            # begin() block has already rolled back; translate the low-level
            # DB error into the same domain error instead of leaking it.
            raise EmailAlreadyExistsError(data.email) from exc

        await self._session.refresh(user)
        return user

    async def authenticate_user(self, data: LoginRequest) -> User:
        """Return the user if email exists and password matches, else raise.

        Read-only: no transaction to commit. Raises the same
        ``InvalidCredentialsError`` whether the email is unknown or the
        password is wrong, so callers cannot probe which emails exist.
        """
        user = await self._users.get_by_email(data.email)
        if user is None:
            # Verify against a dummy hash anyway would be ideal to equalize
            # timing; kept simple here since endpoints/JWT are out of scope.
            raise InvalidCredentialsError()
        if not verify_password(data.password, user.hashed_password):
            raise InvalidCredentialsError()
        return user
