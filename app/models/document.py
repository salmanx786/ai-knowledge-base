from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ORMBase

if TYPE_CHECKING:
    from app.models.user import User


class Document(ORMBase):
    """A PDF document uploaded by a single user.

    Ownership is the whole access model: every row belongs to exactly one
    ``owner_id`` and is only ever reachable through that owner. The FK uses
    ``ON DELETE CASCADE`` so a user's documents are removed with the user.

    ``filename`` is the name the file was uploaded under (for display);
    ``storage_filename`` is the generated on-disk name (a UUID + ``.pdf``).
    The full path is never persisted -- it is derived on demand from the
    upload root, the ``owner_id``, and ``storage_filename`` -- so the storage
    layout can move without a data migration and is never exposed to clients.

    ``extracted_text`` holds the concatenated text of every page, pulled out of
    the PDF once at upload time. It is nullable because the column exists
    independently of extraction ever having run; in practice a successful
    upload always populates it (an empty PDF yields an empty string, not NULL).
    """

    __tablename__ = "documents"

    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        # Every ownership-scoped query filters on owner_id, so index it.
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    owner: Mapped["User"] = relationship()
