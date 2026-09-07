"""Chat (RAG) HTTP endpoints.

Same thin-controller style as the documents router: delegate to ChatService and
translate the one domain error into an HTTPException. The route is protected by
``get_current_user`` and passes the authenticated user's id to the service as
the owner -- the client never supplies ownership, so retrieval is confined to
the caller's own documents.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)


from app.dependencies.auth import get_current_user
from app.dependencies.documents import get_chat_service
from app.models.user import User
from app.repositories.errors import (
    LLMConfigurationError,
    NoRelevantDocumentsError,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Answer a question from the current user's documents",
)
async def chat(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    body: ChatRequest,
) -> ChatResponse:
    """Answer ``question`` using only the authenticated user's document chunks.

    Retrieval is scoped to the caller's own documents. Returns 404 when no
    relevant chunks exist (empty index or no documents), so the caller never
    receives an answer that is not grounded in their own content.
    """
    try:
        return await service.answer_question(
            owner_id=current_user.id,
            question=body.question,
            limit=body.limit,
            conversation_id=body.conversation_id,
        )
    except NoRelevantDocumentsError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant documents found.",
        )
    except LLMConfigurationError as exc:
        logger.error(f"LLM configuration error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM is not configured.",
        )
    except Exception as exc:
        logger.error(f"Unexpected error in chat endpoint: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during chat.",
        )

