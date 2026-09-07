from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.schemas.chat import (
    ConversationDetail,
    ConversationMessage,
    ConversationSummary,
)


router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["conversations"],
)


@router.get(
    "",
    response_model=list[ConversationSummary],
)
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    session=Depends(get_db),
):
    repo = ConversationRepository(session)

    conversations = await repo.list_for_user(
        user_id=current_user.id,
    )

    conversation_ids = [conversation.id for conversation in conversations]

    first_messages = await repo.get_first_user_messages(
        conversation_ids=conversation_ids,
    )

    summaries = []

    for conversation in conversations:
        first_message = first_messages.get(conversation.id)

        title = (
            first_message.content.strip()
            if first_message
            else "New conversation"
        )

        if len(title) > 60:
            title = title[:57].rstrip() + "..."

        summaries.append(
            ConversationSummary(
                id=conversation.id,
                title=title,
                created_at=conversation.created_at.isoformat(),
                updated_at=conversation.updated_at.isoformat(),
            )
        )

    return summaries


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
)
async def get_conversation(
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session=Depends(get_db),
):
    repo = ConversationRepository(session)

    conversation = await repo.get_for_user(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    messages = await repo.list_messages(
        conversation_id=conversation.id,
        limit=100,
    )

    return ConversationDetail(
        id=conversation.id,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        messages=[
            ConversationMessage(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at.isoformat(),
            )
            for message in messages
        ],
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session=Depends(get_db),
):
    repo = ConversationRepository(session)

    deleted = await repo.delete_for_user(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    await session.commit()
