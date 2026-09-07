from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ORMBase

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(ORMBase):
    """One user or assistant message inside a conversation."""

    __tablename__ = "messages"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages"
    )
