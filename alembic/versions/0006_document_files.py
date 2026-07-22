"""simplify documents: replace title/status with filename/file_path

Revision ID: 0006_document_files
Revises: 0005_create_documents
Create Date: 2026-07-21

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006_document_files"
down_revision: str | None = "0005_create_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Recreated on downgrade only, to restore 0005's shape.
_status_enum = sa.Enum(
    "draft",
    "published",
    "archived",
    name="document_status",
    native_enum=False,
    length=32,
)


def upgrade() -> None:
    # An uploaded document is now just its file: the metadata-only title and the
    # lifecycle status are gone. filename is the original client name; file_path
    # is where the bytes landed under the uploads/ root.
    op.add_column(
        "documents",
        sa.Column("filename", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("file_path", sa.String(length=1024), nullable=False),
    )
    op.drop_column("documents", "status")
    op.drop_column("documents", "title")


def downgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("title", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column(
            "status",
            _status_enum,
            server_default="draft",
            nullable=False,
        ),
    )
    op.drop_column("documents", "file_path")
    op.drop_column("documents", "filename")
