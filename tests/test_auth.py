"""Tests for DB-backed OTP rate limiting in auth.py.

All tests use mocked AsyncSession objects so no real database is needed.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.routers.auth import (
    _check_otp_send_rate,
    _check_otp_fail_rate,
    _record_otp_fail,
    _verify_otp,
    _OTP_SEND_MAX,
    _OTP_FAIL_MAX,
)


def _session_returning_count(count: int) -> AsyncMock:
    """Return an AsyncSession mock whose execute().scalar_one() yields *count*."""
    result = MagicMock()
    result.scalar_one.return_value = count
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# ── Smoke test ─────────────────────────────────────────────────────────────────

def test_auth_module_imports_without_error():
    """Importing auth.py must not raise NameError or other import-time errors.

    This is a regression guard for the defaultdict/missing-import bug that caused
    the module to fail before the server could serve any auth routes.
    """
    from app.routers import auth  # noqa: F401 — import is the test

    assert hasattr(auth, "router")
    assert hasattr(auth, "_check_otp_send_rate")
    assert hasattr(auth, "_check_otp_fail_rate")
    assert hasattr(auth, "_record_otp_fail")


# ── Send rate limiting ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_rate_allows_when_below_max():
    session = _session_returning_count(_OTP_SEND_MAX - 1)
    # Must not raise
    await _check_otp_send_rate(session, "user@example.com")


@pytest.mark.asyncio
async def test_send_rate_blocks_exactly_at_max():
    session = _session_returning_count(_OTP_SEND_MAX)
    with pytest.raises(HTTPException) as exc_info:
        await _check_otp_send_rate(session, "user@example.com")
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_send_rate_blocks_above_max():
    session = _session_returning_count(_OTP_SEND_MAX + 5)
    with pytest.raises(HTTPException) as exc_info:
        await _check_otp_send_rate(session, "user@example.com")
    assert exc_info.value.status_code == 429


# ── Fail rate limiting ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fail_rate_allows_when_below_max():
    session = _session_returning_count(_OTP_FAIL_MAX - 1)
    await _check_otp_fail_rate(session, "user@example.com")


@pytest.mark.asyncio
async def test_fail_rate_blocks_exactly_at_max():
    session = _session_returning_count(_OTP_FAIL_MAX)
    with pytest.raises(HTTPException) as exc_info:
        await _check_otp_fail_rate(session, "user@example.com")
    assert exc_info.value.status_code == 429


# ── _record_otp_fail ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_otp_fail_inserts_row():
    session = _session_returning_count(0)
    await _record_otp_fail(session, "user@example.com")

    # One DELETE (prune old rows) + the session.add call must have happened
    session.execute.assert_called_once()
    session.add.assert_called_once()
    added = session.add.call_args[0][0]
    assert added.email == "user@example.com"
    # commit() must be called — flush() alone would be rolled back when the
    # session closes after HTTPException is raised by the caller.
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_verify_otp_commits_fail_before_raising():
    """_verify_otp must commit the OtpFailAttempt before raising HTTPException.

    Regression guard for the flush()-without-commit bug: SQLAlchemy rolls back
    the transaction when the session context manager closes at the end of the
    FastAPI request, so any fail attempt recorded with only flush() is silently
    discarded and _check_otp_fail_rate never accumulates across requests.
    """
    # Three consecutive execute() calls:
    #   1. _check_otp_fail_rate  — returns count 0 (not yet rate-limited)
    #   2. _verify_otp OTP lookup — returns None  (wrong / no matching code)
    #   3. _record_otp_fail prune — return value unused
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    otp_result = MagicMock()
    otp_result.scalar_one_or_none.return_value = None

    prune_result = MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[count_result, otp_result, prune_result])
    session.add = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await _verify_otp(session, "user@example.com", "000000", "login")

    assert exc_info.value.status_code == 400
    # commit() must have been called so the fail attempt survives the request
    session.commit.assert_called_once()
