"""Document domain logic.

The single business rule is ownership: a user may only ever read or delete
their own documents. That rule is expressed once, structurally -- every method
takes the acting ``owner_id`` and passes it through to ownership-scoped
repository queries, so there is no code path that returns another user's row.

File handling is intentionally minimal for this portfolio project: PDFs are
saved directly under ``uploads/<owner_id>/`` with a generated name, then a row
is written. No storage abstraction, no cloud prep, no orphan-cleanup system.

Transaction handling: these endpoints share one request-scoped session with
``get_current_user``, which issues a SELECT (autobegining a transaction) before
the service runs. That rules out ``async with session.begin()`` -- it raises if
a transaction is already open -- so writes commit explicitly and roll back on
failure.
"""

import uuid
from collections.abc import Sequence
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.document import Document
from app.repositories.chunk import DocumentChunkRepository
from app.repositories.document import DocumentRepository
from app.repositories.errors import DocumentNotFoundError
from app.services.chunking import chunk_text
from app.services.embeddings import EmbeddingService
from app.services.pdf_text import extract_pdf_text


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._chunks = DocumentChunkRepository(session)
        self._embeddings = EmbeddingService()

    async def upload_document(
        self, *, owner_id: int, upload: UploadFile
    ) -> Document:
        """Save an uploaded PDF, extract its text, chunk it, embed each chunk,
        and create the rows.

        Order matters: the file is written to disk, its text is extracted, then
        the metadata row (including the text) and its text chunks -- each with
        its embedding -- are committed together in one transaction. If
        extraction fails the saved file is intentionally left in place and
        ``TextExtractionError`` propagates -- no rows are written, nothing is
        deleted. Ownership comes from the authenticated caller, never the
        request.
        """
        # Per-user directory keeps one user's files apart from another's.
        # owner_id is an int from the DB, so it cannot inject path segments.
        user_dir = Path(settings.upload_dir) / str(owner_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # uuid4 name is unique and strips any path the client put in `filename`.
        # Only this basename is persisted; the full path is derived from the
        # upload root + owner_id + storage_filename, never stored or exposed.
        storage_filename = f"{uuid.uuid4().hex}.pdf"
        stored_path = user_dir / storage_filename
        stored_path.write_bytes(await upload.read())

        # Extract before the row is written. On failure this raises
        # TextExtractionError (mapped to 500 upstream); the file above is left
        # on disk by design and no partial row is created.
        extracted_text = extract_pdf_text(stored_path)

        document = await self._documents.create(
            owner_id=owner_id,
            filename=upload.filename or storage_filename,
            storage_filename=storage_filename,
            extracted_text=extracted_text,
        )

        # Chunk the extracted text, embed each chunk, and persist the chunks
        # (text + vector) in the same transaction as the document. chunk_text
        # returns [] for empty or whitespace-only text, so an empty PDF produces
        # no chunk rows and therefore no embeddings at all. document.id is
        # available here because create() flushed. Embedding is synchronous and
        # one chunk at a time by design -- batching and async are out of scope.
        contents = chunk_text(extracted_text)
        if contents:
            embeddings = [self._embeddings.embed(content) for content in contents]
            await self._chunks.create_for_document(
                document_id=document.id,
                contents=contents,
                embeddings=embeddings,
            )

        await self._session.commit()
        await self._session.refresh(document)
        return document

    async def list_documents(self, *, owner_id: int) -> Sequence[Document]:
        """Return every document owned by ``owner_id`` (read-only)."""
        return await self._documents.list_for_user(owner_id=owner_id)

    async def get_document(
        self, *, document_id: int, owner_id: int
    ) -> Document:
        """Return the caller's document or raise ``DocumentNotFoundError``.

        A document that does not exist and one owned by a different user are
        treated identically -- both raise, so the API returns the same 404.
        """
        document = await self._documents.get_for_user(
            document_id=document_id, owner_id=owner_id
        )
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document

    async def delete_document(
        self, *, document_id: int, owner_id: int
    ) -> None:
        """Delete the caller's document or raise ``DocumentNotFoundError``.

        Re-fetches with ownership scoping first so a user can only delete a
        document they own; the lookup and delete share one transaction.
        """
        document = await self._documents.get_for_user(
            document_id=document_id, owner_id=owner_id
        )
        if document is None:
            raise DocumentNotFoundError(document_id)
        await self._documents.delete(document)
        await self._session.commit()
