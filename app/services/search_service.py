from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.chunk import DocumentChunkRepository
from app.schemas.search import SearchResultResponse
from app.services.embeddings import EmbeddingService
from app.services.similarity import cosine_similarity


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._chunks = DocumentChunkRepository(session)
        self._embeddings = EmbeddingService()

    async def search(
        self, *, owner_id: int, query: str, limit: int
    ) -> list[SearchResultResponse]:
        """Embed ``query`` and return the top ``limit`` chunks by cosine similarity.

        Only chunks belonging to the authenticated user's documents are
        considered -- ownership is enforced in the repository query. Chunks
        without an embedding are excluded there too, so the similarity loop
        always operates on valid vectors.
        """
        chunks = await self._chunks.list_for_user(owner_id=owner_id)
        if not chunks:
            return []

        query_vector = self._embeddings.embed(query)

        scored = sorted(
            (
                SearchResultResponse(
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=cosine_similarity(query_vector, chunk.embedding),  # type: ignore[arg-type]
                )
                for chunk in chunks
            ),
            key=lambda r: r.score,
            reverse=True,
        )
        return scored[:limit]
