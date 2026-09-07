from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.chunk import DocumentChunkRepository
from app.schemas.search import SearchResultResponse
from app.services.embeddings import EmbeddingService
from app.services.reranking import RerankingService
from app.services.similarity import cosine_similarity


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._chunks = DocumentChunkRepository(session)
        self._embeddings = EmbeddingService()
        self._reranker = RerankingService()

    async def search(
        self,
        *,
        owner_id: int,
        query: str,
        limit: int,
    ) -> list[SearchResultResponse]:
        """Hybrid retrieval: dense + lexical candidates, then reranking."""

        candidate_limit = max(limit * 4, 20)

        # 1. Dense candidate generation.
        all_chunks = await self._chunks.list_for_user(
            owner_id=owner_id,
        )

        # 2. Lexical candidate generation.
        lexical_chunks = await self._chunks.search_full_text(
            owner_id=owner_id,
            query=query,
            limit=candidate_limit,
        )

        if not all_chunks and not lexical_chunks:
            return []

        query_vector = self._embeddings.embed(query)

        # Score all dense candidates and keep only the top candidate_limit.
        semantic_candidates = sorted(
            (
                (
                    cosine_similarity(
                        query_vector,
                        chunk.embedding,  # type: ignore[arg-type]
                    ),
                    chunk,
                )
                for chunk in all_chunks
            ),
            key=lambda item: item[0],
            reverse=True,
        )[:candidate_limit]

        # 3. Merge dense + lexical candidates by stable chunk identity.
        candidates_by_key = {
            (chunk.document_id, chunk.chunk_index): chunk
            for _, chunk in semantic_candidates
        }

        for chunk in lexical_chunks:
            candidates_by_key.setdefault(
                (chunk.document_id, chunk.chunk_index),
                chunk,
            )

        # 4. Build reranker inputs.
        candidates = []
        semantic_scores = {
            (chunk.document_id, chunk.chunk_index): score
            for score, chunk in semantic_candidates
        }

        for chunk in candidates_by_key.values():
            key = (chunk.document_id, chunk.chunk_index)
            candidates.append(
                SearchResultResponse(
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    semantic_score=semantic_scores.get(key, 0.0),
                )
            )

        # 5. Cross-encoder reranking.
        return self._reranker.rerank(
            query=query,
            results=candidates,
            limit=limit,
        )
