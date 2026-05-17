import time
import uuid
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.otp_code import OTPCode
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
    otp_expires_at,
    otp_is_expired,
)
from app.utils.email_utils import send_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


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
        code=code,
        purpose=purpose,
        expires_at=otp_expires_at(),
        used=False,
    )
    session.add(otp_row)
    await session.commit()


async def _verify_otp(
    session: AsyncSession, email: str, code: str, purpose: str
) -> OTPCode:
    result = await session.execute(
        select(OTPCode).where(
            OTPCode.email == email,
            OTPCode.code == code,
            OTPCode.purpose == purpose,
            OTPCode.used == False,  # noqa: E712
        )
    )
    otp_row = result.scalar_one_or_none()
    if not otp_row:
        raise HTTPException(status_code=400, detail="קוד שגוי")
    if otp_is_expired(otp_row.expires_at):
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
    # Check if email already registered
    result = await session.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="כתובת המייל כבר רשומה במערכת")

    code = generate_otp()
    # Store name temporarily in the code field as JSON? No — we store name in purpose payload.
    # Simpler: store pending registration in OTPCode, name will be supplied again at verify step.
    await _save_otp(session, body.email, code, "register")
    dev_code = await send_otp_email(body.email, code, "register")
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
    # Re-check email not already taken (race condition guard)
    result = await session.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="כתובת המייל כבר רשומה")

    await _verify_otp(session, body.email, body.code, "register")

    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
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
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="לא נמצא משתמש עם מייל זה")

    code = generate_otp()
    await _save_otp(session, body.email, code, "login")
    dev_code = await send_otp_email(body.email, code, "login")
    response: dict = {"detail": "קוד נשלח למייל"}
    if dev_code is not None:
        response["dev_code"] = dev_code
    return response


# ── Login (step 2: verify OTP) ─────────────────────────────────────────────────

@router.post("/login/verify", response_model=TokenResponse, summary="אמת OTP וקבל טוקן")
async def login_verify(
    body: VerifyOTPRequest,
    session: AsyncSession = Depends(get_db),
):
    await _verify_otp(session, body.email, body.code, "login")

    result = await session.execute(select(User).where(User.email == body.email))
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
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    # Always return 200 even if email unknown (prevent user enumeration)
    dev_code: str | None = None
    if user and user.is_active:
        code = generate_otp()
        await _save_otp(session, body.email, code, "reset")
        dev_code = await send_otp_email(body.email, code, "reset")
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
    await _verify_otp(session, body.email, body.code, "reset")

    result = await session.execute(select(User).where(User.email == body.email))
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
