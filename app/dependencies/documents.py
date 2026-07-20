"""Dependency providers for the documents API layer.

Mirrors ``get_auth_service``: constructs a DocumentService bound to the
request-scoped session so route handlers declare ``Depends(get_document_service)``
and never touch sessions or repositories directly.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.services.document_service import DocumentService


async def get_document_service(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[DocumentService, None]:
    """Provide a DocumentService bound to the request's DB session."""
    yield DocumentService(session)
