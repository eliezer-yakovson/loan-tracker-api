"""Initial schema — categories, loans, month_entries

Revision ID: 0001
Revises:
Create Date: 2026-05-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── categories ────────────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── loans ─────────────────────────────────────────────────────────────────
    op.create_table(
        "loans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("category_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("lender_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("original_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_payments", sa.Integer(), nullable=False),
        sa.Column("taken_date", sa.String(10), nullable=False),
        sa.Column("monthly_due_day", sa.SmallInteger(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.CheckConstraint(
            "monthly_due_day BETWEEN 1 AND 31",
            name="ck_loans_due_day",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loans_category_id", "loans", ["category_id"])

    # ── month_entries ─────────────────────────────────────────────────────────
    op.create_table(
        "month_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("loan_id", sa.String(), nullable=False),
        sa.Column("month_key", sa.String(7), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column(
            "confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "manually_edited",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.ForeignKeyConstraint(
            ["loan_id"],
            ["loans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("loan_id", "month_key", name="uq_month_entries_loan_month"),
    )
    op.create_index("ix_month_entries_loan_id", "month_entries", ["loan_id"])
    op.create_index("ix_month_entries_month_key", "month_entries", ["month_key"])


def downgrade() -> None:
    op.drop_table("month_entries")
    op.drop_table("loans")
    op.drop_table("categories")
