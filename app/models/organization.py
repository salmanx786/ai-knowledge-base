from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ORMBase

if TYPE_CHECKING:
    from app.models.organization_member import OrganizationMember


class Organization(ORMBase):
    """Tenant. Users are attached through OrganizationMember, not directly."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
