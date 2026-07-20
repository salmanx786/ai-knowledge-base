"""Document domain logic.

The single business rule is ownership: a user may only ever read or delete
their own documents. That rule is expressed once, structurally -- every method
takes the acting ``owner_id`` and passes it through to ownership-scoped
repository queries, so there is no code path that returns another user's row.

Transaction handling: these endpoints share one request-scoped session with
``get_current_user``, which issues a SELECT (autobegining a transaction) before
the service runs. That rules out ``async with session.begin()`` -- it raises if
a transaction is already open -- so writes commit explicitly and roll back on
failure. ``get_db`` still closes (and thus rolls back) the session if an error
escapes, this just makes the boundary explicit and local.
"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.document import DocumentRepository
from app.repositories.errors import DocumentNotFoundError
from app.schemas.document import DocumentCreate


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = DocumentRepository(session)

    async def create_document(
        self, *, owner_id: int, data: DocumentCreate
    ) -> Document:
        """Create a document owned by ``owner_id``.

        Ownership comes from the authenticated user (the caller), never from
        the request payload, so a client cannot create a document on another
        user's behalf.
        """
        try:
            document = await self._documents.create(
                owner_id=owner_id,
                title=data.title,
                status=data.status,
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        # commit() expired attributes; refresh so the returned instance carries
        # server-generated columns (id, timestamps, status default) for
        # serialization.
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
        try:
            await self._documents.delete(document)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
