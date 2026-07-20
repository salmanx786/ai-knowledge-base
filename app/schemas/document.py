"""Pydantic v2 request/response schemas for documents.

Transport/DTO objects only, in the same style as ``schemas/auth.py``: no ORM
coupling beyond ``from_attributes`` on the response. ``owner_id`` is never part
of a request payload -- ownership is taken from the authenticated user, never
from client input.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class DocumentCreate(BaseModel):
    """Payload to create a document.

    ``status`` is optional so the common case (create a draft) needs only a
    title; it defaults to ``DRAFT`` to match the column's server default.
    """

    title: str = Field(min_length=1, max_length=255)
    status: DocumentStatus = DocumentStatus.DRAFT


class DocumentResponse(BaseModel):
    """Public representation of a document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
