"""Persistence access for Organization and OrganizationMember.

Same contract as UserRepository: these methods add rows and flush to obtain
generated keys, but never commit. The service composes them inside one
transaction so the org + membership are created atomically with the user.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.organization_member import (
    MembershipStatus,
    OrganizationMember,
    OrganizationRole,
)


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str) -> Organization:
        """Add a new organization and flush so ``organization.id`` is available."""
        organization = Organization(name=name)
        self._session.add(organization)
        # flush (not commit) so organization.id is assigned for the membership
        # FK while staying inside the service's transaction. See UserRepository.
        await self._session.flush()
        return organization

    async def add_member(
        self,
        *,
        organization_id: int,
        user_id: int,
        role: OrganizationRole,
        status: MembershipStatus,
    ) -> OrganizationMember:
        """Add a membership row linking a user to an organization. No commit."""
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            status=status,
        )
        self._session.add(member)
        # flush (not commit) to surface constraint violations now while leaving
        # the commit decision to the service that owns the transaction.
        await self._session.flush()
        return member
