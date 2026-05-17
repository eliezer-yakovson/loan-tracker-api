import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

ALGORITHM = "HS256"


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp() -> str:
    """Return a zero-padded 6-digit OTP string."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str) -> str:
    """HMAC-SHA256 of the OTP code keyed by the server secret.
    Stored instead of plaintext so a DB compromise alone cannot reveal active codes.
    """
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def otp_expires_at() -> float:
    """Unix timestamp 10 minutes from now."""
    return time.time() + 600


def otp_is_expired(expires_at: float) -> bool:
    return time.time() > expires_at


# ── JWT ────────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.token_expire_days)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
