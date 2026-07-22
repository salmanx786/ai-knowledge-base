"""add extracted_text to documents

Revision ID: 0007_document_extracted_text
Revises: 0006_document_files
Create Date: 2026-07-22

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007_document_extracted_text"
down_revision: str | None = "0006_document_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The full page text extracted from the PDF at upload time. Nullable: the
    # column is independent of whether extraction has run for a given row.
    op.add_column(
        "documents",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "extracted_text")
