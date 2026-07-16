"""separate identity from membership: add organization_members, drop users.organization_id

Revision ID: 0004_org_members
Revises: 0003_add_user_hashed_password
Create Date: 2026-07-16

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_org_members"
down_revision: str | None = "0003_add_user_hashed_password"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# String-backed enums (native_enum=False) -> VARCHAR + CHECK constraint.
_role_enum = sa.Enum(
    "owner",
    "admin",
    "member",
    name="organization_role",
    native_enum=False,
    length=32,
)
_status_enum = sa.Enum(
    "active",
    "invited",
    "suspended",
    name="membership_status",
    native_enum=False,
    length=32,
)


def upgrade() -> None:
    # 1. Identity/membership separation: users no longer carry an org.
    #    Dropping the column cascades to its FK; drop its index explicitly first.
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_column("users", "organization_id")

    # 2. The join entity between User (identity) and Organization (tenant).
    op.create_table(
        "organization_members",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "role",
            _role_enum,
            server_default="member",
            nullable=False,
        ),
        sa.Column(
            "status",
            _status_enum,
            server_default="active",
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
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_org_member_org_user"
        ),
    )
    # Reverse-direction lookups ("which orgs is this user in?"). The forward
    # direction is already served by the leading column of the unique index.
    op.create_index(
        "ix_organization_members_user_id",
        "organization_members",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_members_user_id",
        table_name="organization_members",
    )
    op.drop_table("organization_members")

    # Re-add the column as nullable: prior rows' org assignments are not
    # recoverable, so a NOT NULL restore could fail on a populated table.
    op.add_column(
        "users",
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_users_organization_id",
        "users",
        ["organization_id"],
    )
    op.create_foreign_key(
        "users_organization_id_fkey",
        "users",
        "organizations",
        ["organization_id"],
        ["organizations.id"],
        ondelete="CASCADE",
    )
