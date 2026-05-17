"""Add user_id to categories and loans

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── categories ──────────────────────────────────────────────────────────
    # Drop the old global unique constraint on name
    op.drop_constraint("categories_name_key", "categories", type_="unique")

    # Add user_id column (nullable first so existing rows don't violate NOT NULL)
    op.add_column(
        "categories",
        sa.Column("user_id", sa.String(), nullable=True),
    )

    # Delete orphan categories that have no corresponding user (clean slate)
    op.execute("DELETE FROM categories")

    # Now make it NOT NULL and add FK
    op.alter_column("categories", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_categories_user_id",
        "categories",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.create_unique_constraint(
        "uq_categories_user_name", "categories", ["user_id", "name"]
    )

    # ── loans ────────────────────────────────────────────────────────────────
    op.add_column(
        "loans",
        sa.Column("user_id", sa.String(), nullable=True),
    )

    # Delete orphan loans too (cascade would handle month_entries)
    op.execute("DELETE FROM loans")

    op.alter_column("loans", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_loans_user_id",
        "loans",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_loans_user_id", "loans", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_loans_user_id", "loans")
    op.drop_constraint("fk_loans_user_id", "loans", type_="foreignkey")
    op.drop_column("loans", "user_id")

    op.drop_constraint("uq_categories_user_name", "categories", type_="unique")
    op.drop_index("ix_categories_user_id", "categories")
    op.drop_constraint("fk_categories_user_id", "categories", type_="foreignkey")
    op.drop_column("categories", "user_id")
    op.create_unique_constraint("categories_name_key", "categories", ["name"])
