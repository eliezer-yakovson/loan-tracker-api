import uuid

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OtpFailAttempt(Base):
    """One row per failed OTP verification — used for DB-backed fail rate limiting.

    Rows older than the rate-limit window are pruned on each write so the table
    stays small without a separate cleanup job.
    """

    __tablename__ = "otp_fail_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Unix timestamp — stored as float to match otp_codes.expires_at convention
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
