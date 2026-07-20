import enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ORMBase

if TYPE_CHECKING:
    from app.models.user import User


class DocumentStatus(enum.StrEnum):
    """Lifecycle state of a document.

    ``DRAFT`` is the default a document is created in; the other states exist so
    the status column is meaningful from day one without implying any workflow
    engine (transitions are not enforced here).
    """

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# VARCHAR + CHECK constraint (native_enum=False), matching OrganizationMember's
# enums: adding a status later is a CHECK swap rather than an ALTER TYPE (which
# cannot run in a transaction). values_callable persists the lowercase .value.
_STATUS_ENUM = Enum(
    DocumentStatus,
    native_enum=False,
    length=32,
    name="document_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Document(ORMBase):
    """A document owned by a single user.

    Ownership is the whole access model for now: every row belongs to exactly
    one ``owner_id`` and is only ever reachable through that owner. The FK uses
    ``ON DELETE CASCADE`` so a user's documents are removed with the user.
    """

    __tablename__ = "documents"

    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        # Every ownership-scoped query filters on owner_id, so index it.
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        _STATUS_ENUM,
        nullable=False,
        server_default=DocumentStatus.DRAFT.value,
    )

    owner: Mapped["User"] = relationship()
