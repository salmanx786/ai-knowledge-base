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

import logging
import uuid
from collections.abc import Sequence
from pathlib import Path

logger = logging.getLogger(__name__)


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
        extraction fails the saved file is cleaned up and
        ``TextExtractionError`` propagates -- no rows are written, nothing is
        leaked on disk. Ownership comes from the authenticated caller, never the
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
        key = f"{owner_id}/{storage_filename}"

        try:
            from app.services.storage import StorageService
            storage = StorageService()
            # Since upload.file is a file-like object, upload it to S3
            storage.upload_fileobj(upload.file, key)

            document = await self._documents.create(
                owner_id=owner_id,
                filename=upload.filename or storage_filename,
                storage_filename=storage_filename,
                extracted_text=None,
            )
            document.status = "pending"
            await self._session.commit()
            await self._session.refresh(document)
            
            # Enqueue the background task via procrastinate
            from app.worker import process_document_task
            await process_document_task.defer_async(document_id=document.id)
            
            return document
        except Exception as exc:
            logger.error(f"Failed to upload document: {exc}", exc_info=True)
            raise exc


    async def list_documents(
        self, *, owner_id: int, limit: int = 10, offset: int = 0
    ) -> Sequence[Document]:
        """Return every document owned by ``owner_id`` (read-only, paginated)."""
        return await self._documents.list_for_user(
            owner_id=owner_id, limit=limit, offset=offset
        )


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

        # Keep track of file path before deleting DB record
        storage_filename = document.storage_filename
        stored_path = Path(settings.upload_dir) / str(owner_id) / storage_filename

        await self._documents.delete(document)
        await self._session.commit()

        # Delete physical file from S3 AFTER successful commit
        key = f"{owner_id}/{storage_filename}"
        try:
            from app.services.storage import StorageService
            storage = StorageService()
            storage.delete_object(key)
        except Exception as exc:
            logger.warning(f"Failed to delete physical file {key} from S3 on document deletion: {exc}")

