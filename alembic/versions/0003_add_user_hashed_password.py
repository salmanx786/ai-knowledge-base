"""add hashed_password to users

Revision ID: 0003_add_user_hashed_password
Revises: 0002_create_users
Create Date: 2026-07-16

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_add_user_hashed_password"
down_revision: str | None = "0002_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
