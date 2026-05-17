"""Widen otp_codes.code to store HMAC-SHA256 hashes instead of plaintext

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen the column from VARCHAR(6) to VARCHAR(64) to hold a SHA-256 hex digest.
    # Existing rows contain plaintext codes that can no longer be verified after this
    # migration (the server now stores HMAC hashes). Invalidate them by marking all
    # current, unexpired codes as used so users simply request a fresh OTP.
    op.execute(
        "UPDATE otp_codes SET used = TRUE WHERE used = FALSE"
    )
    op.alter_column(
        "otp_codes",
        "code",
        existing_type=sa.String(6),
        type_=sa.String(64),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Clear hashed codes before narrowing — they cannot be truncated safely.
    op.execute("UPDATE otp_codes SET used = TRUE WHERE used = FALSE")
    op.alter_column(
        "otp_codes",
        "code",
        existing_type=sa.String(64),
        type_=sa.String(6),
        existing_nullable=False,
    )
