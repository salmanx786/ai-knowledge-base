from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


class ConversationRepository:
    """Persistence operations for conversations and messages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: int) -> Conversation:
        conversation = Conversation(user_id=user_id)
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def list_for_user(
        self,
        *,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_for_user(
        self,
        *,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_first_user_messages(
        self,
        *,
        conversation_ids: Sequence[int],
    ) -> dict[int, Message]:
        if not conversation_ids:
            return {}

        result = await self._session.execute(
            select(Message)
            .where(
                Message.conversation_id.in_(conversation_ids),
                Message.role == "user",
            )
            .order_by(Message.conversation_id, Message.created_at.asc())
        )

        messages: dict[int, Message] = {}

        for message in result.scalars():
            messages.setdefault(message.conversation_id, message)

        return messages

    async def list_messages(
        self,
        *,
        conversation_id: int,
        limit: int = 10,
    ) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )

        return list(reversed(result.scalars().all()))

    async def add_message(
        self,
        *,
        conversation_id: int,
        role: str,
        content: str,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def delete_for_user(
        self,
        *,
        conversation_id: int,
        user_id: int,
    ) -> bool:
        result = await self._session.execute(
            delete(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.rowcount > 0
