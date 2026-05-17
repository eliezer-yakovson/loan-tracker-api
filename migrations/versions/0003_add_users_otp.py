"""Add users and otp_codes tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "otp_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False, server_default="login"),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_otp_codes_email", "otp_codes", ["email"])


def downgrade() -> None:
    op.drop_index("ix_otp_codes_email", table_name="otp_codes")
    op.drop_table("otp_codes")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
