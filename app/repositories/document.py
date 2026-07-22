"""Persistence access for the Document entity.

Same contract as the other repositories: methods translate intent into
SQLAlchemy queries and operate on the injected session, but never open or
commit transactions -- the service owns the unit of work. ``create`` flushes so
the generated primary key is populated without committing.

Every read is *ownership-scoped*: ``owner_id`` is a required argument, not an
optional filter, so it is impossible to accidentally load another user's row
through this repository.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        owner_id: int,
        filename: str,
        storage_filename: str,
        extracted_text: str | None = None,
    ) -> Document:
        """Add a new document and flush so ``document.id`` is available. No commit."""
        document = Document(
            owner_id=owner_id,
            filename=filename,
            storage_filename=storage_filename,
            extracted_text=extracted_text,
        )
        self._session.add(document)
        # flush (not commit) so the DB assigns document.id and surfaces any
        # constraint violation here, while the write stays part of the
        # service's transaction. See UserRepository for the full rationale.
        await self._session.flush()
        return document

    async def list_for_user(self, *, owner_id: int) -> Sequence[Document]:
        """Return all documents owned by this user, newest first."""
        result = await self._session.execute(
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()

    async def get_for_user(
        self, *, document_id: int, owner_id: int
    ) -> Document | None:
        """Return the document if it exists *and* is owned by this user.

        Ownership is part of the WHERE clause, so "not found" and "belongs to
        someone else" are indistinguishable at this layer -- both return
        ``None``. That is what lets the API return an identical 404 for both,
        avoiding an existence oracle.
        """
        result = await self._session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, document: Document) -> None:
        """Delete a document. No commit -- the service owns the transaction.

        Takes an already-loaded (and therefore already ownership-verified)
        instance rather than an id, so this method cannot be used to delete a
        row the caller has not first fetched through ``get_for_user``.
        """
        await self._session.delete(document)
        await self._session.flush()
