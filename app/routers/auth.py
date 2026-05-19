import time
import uuid
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.otp_code import OTPCode
from app.models.otp_fail_attempt import OtpFailAttempt
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    RegisterVerifyRequest,
    SendOTPRequest,
    TokenResponse,
    UserOut,
    VerifyOTPRequest,
)
from app.utils.auth_utils import (
    create_access_token,
    decode_access_token,
    generate_otp,
    hash_otp,
    otp_expires_at,
    otp_is_expired,
)
from app.utils.email_utils import send_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)

# ── DB-backed OTP rate limiters (durable across restarts and multiple workers) ─
# NOTE: _OTP_SEND_WINDOW must equal the OTP TTL set in otp_expires_at() (600 s)
# so that counting un-expired rows == counting sends in the last 10 minutes.
_OTP_SEND_WINDOW = 600   # 10 minutes
_OTP_SEND_MAX = 3        # max 3 OTP sends per window

_OTP_FAIL_WINDOW = 300   # 5 minutes
_OTP_FAIL_MAX = 10       # max 10 failed attempts per window


async def _check_otp_send_rate(session: AsyncSession, email: str) -> None:
    """Block if this email has sent >= _OTP_SEND_MAX OTPs in the last 10 minutes.

    Uses otp_codes.expires_at as a creation-time proxy: because the OTP TTL equals
    the send window (both 600 s), any OTP that has not yet expired was sent within
    the current window.
    """
    now = time.time()
    result = await session.execute(
        select(func.count()).select_from(OTPCode).where(
            OTPCode.email == email,
            OTPCode.expires_at > now,
        )
    )
    if result.scalar_one() >= _OTP_SEND_MAX:
        raise HTTPException(
            status_code=429,
            detail="שלחת יותר מדי קודות בזמן קצר. נסה שוב בעוד 10 דקות.",
        )


async def _check_otp_fail_rate(session: AsyncSession, email: str) -> None:
    """Block if this email has >= _OTP_FAIL_MAX failures in the last 5 minutes."""
    now = time.time()
    result = await session.execute(
        select(func.count()).select_from(OtpFailAttempt).where(
            OtpFailAttempt.email == email,
            OtpFailAttempt.created_at > now - _OTP_FAIL_WINDOW,
        )
    )
    if result.scalar_one() >= _OTP_FAIL_MAX:
        raise HTTPException(
            status_code=429,
            detail="יותר מדי ניסיונות כושלים. נסה שוב בעוד 5 דקות.",
        )


async def _record_otp_fail(session: AsyncSession, email: str) -> None:
    """Record a failed OTP attempt and prune entries outside the window.

    Uses commit() (not flush()) so the row survives even though the caller
    raises HTTPException immediately after.  FastAPI catches HTTPException and
    returns a normal HTTP response, but the session context manager in get_db()
    never issues an explicit commit for the error path — a plain flush() would
    therefore be rolled back when the session closes.
    """
    now = time.time()
    await session.execute(
        delete(OtpFailAttempt).where(
            OtpFailAttempt.created_at < now - _OTP_FAIL_WINDOW
        )
    )
    session.add(OtpFailAttempt(id=str(uuid.uuid4()), email=email, created_at=now))
    await session.commit()


# ── Dependency: get current authenticated user ─────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="לא מחובר")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload["sub"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="טוקן לא תקין")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="משתמש לא נמצא")
    return user


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _save_otp(session: AsyncSession, email: str, code: str, purpose: str) -> None:
    """Invalidate old unused OTPs for this email+purpose and save a fresh one."""
    old_result = await session.execute(
        select(OTPCode).where(
            OTPCode.email == email,
            OTPCode.purpose == purpose,
            OTPCode.used == False,  # noqa: E712
        )
    )
    for old in old_result.scalars():
        old.used = True  # mark old codes as used

    otp_row = OTPCode(
        id=str(uuid.uuid4()),
        email=email,
        code=hash_otp(code),  # store HMAC hash, never plaintext
        purpose=purpose,
        expires_at=otp_expires_at(),
        used=False,
    )
    session.add(otp_row)
    await session.commit()


async def _verify_otp(
    session: AsyncSession, email: str, code: str, purpose: str
) -> OTPCode:
    await _check_otp_fail_rate(session, email)
    result = await session.execute(
        select(OTPCode).where(
            OTPCode.email == email,
            OTPCode.code == hash_otp(code),  # compare against stored HMAC hash
            OTPCode.purpose == purpose,
            OTPCode.used == False,  # noqa: E712
        )
    )
    otp_row = result.scalar_one_or_none()
    if not otp_row:
        await _record_otp_fail(session, email)
        raise HTTPException(status_code=400, detail="קוד שגוי")
    if otp_is_expired(otp_row.expires_at):
        await _record_otp_fail(session, email)
        raise HTTPException(status_code=400, detail="הקוד פג תוקף, שלח קוד חדש")
    otp_row.used = True
    await session.commit()
    return otp_row


# ── Register (step 1: send OTP) ────────────────────────────────────────────────

@router.post("/register/send-otp", summary="שלב 1: שלח OTP להרשמה")
async def register_send_otp(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    email = body.email.strip().lower()
    await _check_otp_send_rate(session, email)
    # Check if email already registered
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="כתובת המייל כבר רשומה במערכת")

    code = generate_otp()
    await _save_otp(session, email, code, "register")
    dev_code = await send_otp_email(email, code, "register")
    response: dict = {"detail": "קוד נשלח למייל"}
    if dev_code is not None:
        response["dev_code"] = dev_code
    return response


# ── Register (step 2: verify OTP + create user) ────────────────────────────────

@router.post("/register/verify", response_model=TokenResponse, summary="שלב 2: אמת OTP והשלם הרשמה")
async def register_verify(
    body: RegisterVerifyRequest,
    session: AsyncSession = Depends(get_db),
):
    email = body.email.strip().lower()
    # Re-check email not already taken (race condition guard)
    result = await session.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="כתובת המייל כבר רשומה")

    await _verify_otp(session, email, body.code, "register")

    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        name=body.name,
        created_at=now,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
        is_admin=user.is_admin,
    )


# ── Login (step 1: send OTP) ───────────────────────────────────────────────────

@router.post("/login/send-otp", summary="שלח OTP לכניסה")
async def login_send_otp(
    body: SendOTPRequest,
    session: AsyncSession = Depends(get_db),
):
    email = body.email.strip().lower()
    await _check_otp_send_rate(session, email)
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    # Always return 200 regardless of whether the email exists — prevents user enumeration.
    # An OTP is only generated and sent when the user actually exists.
    dev_code: str | None = None
    if user and user.is_active:
        code = generate_otp()
        await _save_otp(session, email, code, "login")
        dev_code = await send_otp_email(email, code, "login")
    response: dict = {"detail": "אם המייל רשום, קוד נשלח אליו"}
    if dev_code is not None:
        response["dev_code"] = dev_code
    return response


# ── Login (step 2: verify OTP) ─────────────────────────────────────────────────

@router.post("/login/verify", response_model=TokenResponse, summary="אמת OTP וקבל טוקן")
async def login_verify(
    body: VerifyOTPRequest,
    session: AsyncSession = Depends(get_db),
):
    email = body.email.strip().lower()
    await _verify_otp(session, email, body.code, "login")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")

    token = create_access_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
        is_admin=user.is_admin,
    )


# ── Forgot / Reset (step 1: send OTP) ─────────────────────────────────────────

@router.post("/reset/send-otp", summary="שלח OTP לאיפוס גישה")
async def reset_send_otp(
    body: SendOTPRequest,
    session: AsyncSession = Depends(get_db),
):
    email = body.email.strip().lower()
    await _check_otp_send_rate(session, email)
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    # Always return 200 even if email unknown (prevent user enumeration)
    dev_code: str | None = None
    if user and user.is_active:
        code = generate_otp()
        await _save_otp(session, email, code, "reset")
        dev_code = await send_otp_email(email, code, "reset")
    response: dict = {"detail": "אם המייל רשום, קוד נשלח אליו"}
    if dev_code is not None:
        response["dev_code"] = dev_code
    return response


# ── Forgot / Reset (step 2: verify OTP) ───────────────────────────────────────

@router.post("/reset/verify", response_model=TokenResponse, summary="אמת OTP לאיפוס")
async def reset_verify(
    body: VerifyOTPRequest,
    session: AsyncSession = Depends(get_db),
):
    email = body.email.strip().lower()
    await _verify_otp(session, email, body.code, "reset")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")

    token = create_access_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
        is_admin=user.is_admin,
    )


# ── Get current user ────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut, summary="פרטי המשתמש המחובר")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Logout (client-side token drop, server returns 200) ───────────────────────

@router.post("/logout", summary="התנתק")
async def logout():
    return {"detail": "התנתקת בהצלחה"}
