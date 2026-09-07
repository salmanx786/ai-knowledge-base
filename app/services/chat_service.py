"""RAG chat orchestration with lightweight conversation memory."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.conversation import ConversationRepository
from app.repositories.errors import NoRelevantDocumentsError
from app.schemas.chat import ChatResponse, ChatSource
from app.services import llm
from app.services.search_service import SearchService


SYSTEM_INSTRUCTION = (
    "You answer ONLY from the supplied document context. "
    "Use the conversation history only to understand what the user is "
    "referring to. Do not treat conversation history as factual evidence. "
    'If the answer is not present in the supplied document context, reply exactly: '
    '"I don\'t know." '
    "Do not use outside knowledge."
)


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self._search = SearchService(session)
        self._conversations = ConversationRepository(session)
        self._session = session

    async def answer_question(
        self,
        *,
        owner_id: int,
        question: str,
        limit: int,
        conversation_id: int | None = None,
    ) -> ChatResponse:
        """Answer a question using owned documents and recent conversation."""

        # ---------------------------------------------------------------
        # 1. Get or create the conversation.
        # ---------------------------------------------------------------
        if conversation_id is None:
            conversation = await self._conversations.create(
                user_id=owner_id,
            )
        else:
            conversation = await self._conversations.get_for_user(
                conversation_id=conversation_id,
                user_id=owner_id,
            )

            if conversation is None:
                # Treat a conversation belonging to another user as if it
                # doesn't exist. This prevents cross-user access.
                raise NoRelevantDocumentsError()

        # ---------------------------------------------------------------
        # 2. Load recent history BEFORE saving the current question.
        # ---------------------------------------------------------------
        history = await self._conversations.list_messages(
            conversation_id=conversation.id,
            limit=10,
        )

        # Build a small retrieval query from recent conversation + question.
        #
        # This avoids an additional Gemini call just to rewrite the question.
        # The embedding model sees the current question together with recent
        # conversational context.
        history_for_retrieval = "\n".join(
            f"{message.role}: {message.content}"
            for message in history
        )

        retrieval_query = (
            f"{history_for_retrieval}\n"
            f"user: {question}"
            if history_for_retrieval
            else question
        )

        # ---------------------------------------------------------------
        # 3. Retrieve document evidence.
        # ---------------------------------------------------------------
        results = await self._search.search(
            owner_id=owner_id,
            query=retrieval_query,
            limit=limit,
        )

        if not results:
            raise NoRelevantDocumentsError()

        # ---------------------------------------------------------------
        # 4. Build document context.
        # ---------------------------------------------------------------
        context = "\n\n".join(
            result.content
            for result in results
        )

        # ---------------------------------------------------------------
        # 5. Build conversation context for Gemini.
        # ---------------------------------------------------------------
        conversation_context = "\n".join(
            f"{message.role.upper()}: {message.content}"
            for message in history
        )

        answer = llm.generate_answer(
            system=SYSTEM_INSTRUCTION,
            context=context,
            question=(
                f"Conversation history:\n"
                f"{conversation_context or '(none)'}\n\n"
                f"Current user question:\n"
                f"{question}"
            ),
        )

        # ---------------------------------------------------------------
        # 6. Persist both sides of the exchange.
        # ---------------------------------------------------------------
        await self._conversations.add_message(
            conversation_id=conversation.id,
            role="user",
            content=question,
        )

        await self._conversations.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
        )

        await self._session.commit()

        return ChatResponse(
            answer=answer,
            conversation_id=conversation.id,
            sources=[
                ChatSource(
                    document_id=result.document_id,
                    chunk_index=result.chunk_index,
                )
                for result in results
            ],
        )
