"""add pgvector and status

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-04 15:08:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the vector extension if it doesn't exist
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Add status and error_message to documents
    op.add_column("documents", sa.Column("status", sa.String(length=50), server_default="pending", nullable=False))
    op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))

    # Migrate embedding from JSON to Vector(768)
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768) USING (embedding::text::vector);")
    
    # Add HNSW index
    op.execute("CREATE INDEX ix_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_l2_ops);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding;")
    
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE json USING (embedding::text::json);")
    
    op.drop_column("documents", "error_message")
    op.drop_column("documents", "status")
    
    op.execute("DROP EXTENSION IF EXISTS vector;")

