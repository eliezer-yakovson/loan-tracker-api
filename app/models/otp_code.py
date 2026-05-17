import uuid
from sqlalchemy import Boolean, String, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    # "register" | "login" | "reset"
    purpose: Mapped[str] = mapped_column(String(20), nullable=False, default="login")
    expires_at: Mapped[float] = mapped_column(Float, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
