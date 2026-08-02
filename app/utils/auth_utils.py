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


# ── Password (PBKDF2-HMAC-SHA256, stdlib only — no extra dependency) ────────────

_PBKDF2_ITERATIONS = 200_000
_PBKDF2_ALGO = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    """Return a self-describing password hash: 'pbkdf2_sha256$iters$salt$hash'."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time verify a plaintext password against a stored PBKDF2 hash."""
    if not stored:
        return False
    try:
        algo, iterations_s, salt_hex, hash_hex = stored.split("$")
        if algo != _PBKDF2_ALGO:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations_s)
        )
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


# ── JWT ────────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.token_expire_days)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
