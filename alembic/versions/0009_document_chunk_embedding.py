"""add embedding to document_chunks

Revision ID: 0009_document_chunk_embedding
Revises: 0008_create_document_chunks
Create Date: 2026-07-22

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009_document_chunk_embedding"
down_revision: str | None = "0008_create_document_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The chunk's vector representation, stored as a JSON array of floats.
    # Nullable: the column is independent of whether an embedding has been
    # generated for a given row. JSON (not pgvector) keeps a real vector store
    # deliberately out of scope for now.
    op.add_column(
        "document_chunks",
        sa.Column("embedding", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_chunks", "embedding")
