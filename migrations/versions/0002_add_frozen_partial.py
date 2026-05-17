"""Add is_frozen and partial_percentage to loans

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "loans",
        sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "loans",
        sa.Column(
            "partial_percentage",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="100.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("loans", "partial_percentage")
    op.drop_column("loans", "is_frozen")
