"""Persistence access for the DocumentChunk entity."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.document import Document


class DocumentChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_for_document(
        self,
        *,
        document_id: int,
        contents: Sequence[str],
        embeddings: Sequence[list[float]],
    ) -> list[DocumentChunk]:
        """Add ordered chunks and their embeddings without committing."""
        chunks = [
            DocumentChunk(
                document_id=document_id,
                chunk_index=index,
                content=content,
                embedding=embedding,
            )
            for index, (content, embedding) in enumerate(
                zip(contents, embeddings, strict=True)
            )
        ]
        self._session.add_all(chunks)
        await self._session.flush()
        return chunks

    async def search_semantic(
        self,
        *,
        owner_id: int,
        query_vector: list[float],
        limit: int,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        """Return the closest pgvector matches for the user."""
        
        result = await self._session.execute(
            select(
                DocumentChunk,
                DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                Document.owner_id == owner_id,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        return result.all()

    async def search_full_text(
        self,
        *,
        owner_id: int,
        query: str,
        limit: int,
    ) -> Sequence[DocumentChunk]:
        """Return the strongest PostgreSQL full-text matches for the user."""

        ts_query = func.websearch_to_tsquery("english", query)

        result = await self._session.execute(
            select(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                Document.owner_id == owner_id,
                DocumentChunk.embedding.is_not(None),
                DocumentChunk.search_vector.op("@@")(ts_query),
            )
            .order_by(
                func.ts_rank_cd(
                    DocumentChunk.search_vector,
                    ts_query,
                ).desc()
            )
            .limit(limit)
        )

        return result.scalars().all()
