from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ORMBase

if TYPE_CHECKING:
    from app.models.organization_member import OrganizationMember


class User(ORMBase):
    """Identity only. Organization membership lives on OrganizationMember."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=true(),
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
