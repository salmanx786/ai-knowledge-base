"""create documents

Revision ID: 0005_create_documents
Revises: 0004_org_members
Create Date: 2026-07-20

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_create_documents"
down_revision: str | None = "0004_org_members"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# String-backed enum (native_enum=False) -> VARCHAR + CHECK constraint, matching
# the model and the organization_members enums.
_status_enum = sa.Enum(
    "draft",
    "published",
    "archived",
    name="document_status",
    native_enum=False,
    length=32,
)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            _status_enum,
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Every ownership-scoped query filters on owner_id.
    op.create_index(
        "ix_documents_owner_id",
        "documents",
        ["owner_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_table("documents")
