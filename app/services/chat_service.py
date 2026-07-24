"""RAG chat orchestration.

ChatService owns the retrieve-augment-generate flow: it asks SearchService for
the most relevant chunks the user owns, builds the prompt from them, and hands
that to the ``llm`` module for an answer. It deliberately depends on both
collaborators through their narrow surfaces -- ``SearchService.search`` and
``llm.generate_answer`` -- and never touches repositories or the Gemini SDK
itself. Ownership is enforced upstream by SearchService, so this service only
passes ``owner_id`` through and never trusts client-supplied identity.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.errors import NoRelevantDocumentsError
from app.schemas.chat import ChatResponse, ChatSource
from app.services import llm
from app.services.search_service import SearchService

# Standing instruction that grounds the model in the retrieved context and
# forbids it from answering from its own knowledge. The exact-string fallback is
# what makes an unrelated question return "I don't know." rather than a
# hallucinated answer drawn from the model's own training data.
SYSTEM_INSTRUCTION = (
    "You answer ONLY from the supplied document context. "
    'If the answer is not present in the supplied context, reply exactly: '
    '"I don\'t know." '
    "Do not use outside knowledge."
)


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self._search = SearchService(session)

    async def answer_question(
        self, *, owner_id: int, question: str, limit: int
    ) -> ChatResponse:
        """Answer ``question`` from the user's own documents.

        Retrieves the top ``limit`` chunks owned by ``owner_id`` via
        SearchService, builds the grounded prompt, and returns the model's
        answer alongside the chunks that fed it. Raises
        ``NoRelevantDocumentsError`` when retrieval yields nothing -- an empty
        index or a user with no documents -- which the API maps to a 404.
        """
        results = await self._search.search(
            owner_id=owner_id, query=question, limit=limit
        )
        if not results:
            raise NoRelevantDocumentsError()

        context = "\n\n".join(result.content for result in results)
        answer = llm.generate_answer(
            system=SYSTEM_INSTRUCTION,
            context=context,
            question=question,
        )

        return ChatResponse(
            answer=answer,
            sources=[
                ChatSource(
                    document_id=result.document_id,
                    chunk_index=result.chunk_index,
                )
                for result in results
            ],
        )
