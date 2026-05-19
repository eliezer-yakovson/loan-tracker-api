"""Add otp_fail_attempts table for DB-backed OTP fail rate limiting

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "otp_fail_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.Float, nullable=False),
    )
    op.create_index("ix_otp_fail_attempts_email", "otp_fail_attempts", ["email"])


def downgrade() -> None:
    op.drop_index("ix_otp_fail_attempts_email", table_name="otp_fail_attempts")
    op.drop_table("otp_fail_attempts")
