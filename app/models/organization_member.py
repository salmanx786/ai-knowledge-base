import enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ORMBase

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class OrganizationRole(enum.StrEnum):
    """Role a member holds within an organization (foundation for RBAC)."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class MembershipStatus(enum.StrEnum):
    """Lifecycle state of a membership (foundation for invitations)."""

    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"


# Stored as VARCHAR + CHECK constraint (native_enum=False) rather than a
# PostgreSQL native ENUM. Adding a role/status later is a CHECK swap instead of
# an ALTER TYPE, which cannot run in a transaction and cannot drop values.
# values_callable persists the lowercase .value (not the member .name).
_ROLE_ENUM = Enum(
    OrganizationRole,
    native_enum=False,
    length=32,
    name="organization_role",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)
_STATUS_ENUM = Enum(
    MembershipStatus,
    native_enum=False,
    length=32,
    name="membership_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class OrganizationMember(ORMBase):
    """Join entity between User (identity) and Organization (tenant).

    Carries the relationship's own attributes -- role and status -- so the
    same user can hold different roles across organizations, and invitations
    exist as membership rows before/without an active user session.
    """

    __tablename__ = "organization_members"
    __table_args__ = (
        # A user has at most one membership per organization.
        UniqueConstraint(
            "organization_id", "user_id", name="uq_org_member_org_user"
        ),
    )

    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[OrganizationRole] = mapped_column(
        _ROLE_ENUM,
        nullable=False,
        server_default=OrganizationRole.MEMBER.value,
    )
    status: Mapped[MembershipStatus] = mapped_column(
        _STATUS_ENUM,
        nullable=False,
        server_default=MembershipStatus.ACTIVE.value,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="memberships",
    )
    user: Mapped["User"] = relationship(
        back_populates="memberships",
    )
