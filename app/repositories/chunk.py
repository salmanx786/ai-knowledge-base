"""Persistence access for the DocumentChunk entity.

Same contract as the other repositories: methods translate intent into
SQLAlchemy queries and operate on the injected session, but never open or commit
transactions -- the service owns the unit of work.

Chunks are always accessed as a group belonging to one document, so there is no
single-row getter here: ``create_for_document`` writes an ordered batch and
``list_for_document`` reads it back in ``chunk_index`` order.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk


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
        """Add ``contents`` as chunks 0..n-1 for a document, in order. No commit.

        ``chunk_index`` is assigned from each item's position in ``contents``, so
        the caller's ordering is the persisted ordering. ``embeddings`` is the
        parallel vector for each content (same length, same order); each chunk
        is created carrying its embedding, so text and vector land in one write.
        Flushes (not commits) so generated ids are populated and any constraint
        violation surfaces here, while the write stays part of the service's
        transaction.
        """
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

    async def list_for_document(
        self, *, document_id: int
    ) -> Sequence[DocumentChunk]:
        """Return a document's chunks ordered by ``chunk_index`` (read-only)."""
        result = await self._session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return result.scalars().all()
