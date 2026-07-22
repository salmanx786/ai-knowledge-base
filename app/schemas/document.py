"""Pydantic v2 response schema for documents.

Transport/DTO object only, in the same style as ``schemas/auth.py``: no ORM
coupling beyond ``from_attributes``. There is no request schema -- a document is
created by uploading a file (multipart), not by posting JSON.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Public representation of an uploaded document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    filename: str
    extracted_text: str | None
    created_at: datetime
    updated_at: datetime
