import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_PURPOSE_LABELS = {
    "register": "רישום חשבון",
    "login": "כניסה לחשבון",
    "reset": "איפוס גישה",
}

_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _build_html(otp_code: str, purpose: str) -> str:
    label = _PURPOSE_LABELS.get(purpose, "אימות")
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f8fa;margin:0;padding:0">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px">
      <table width="480" style="background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.08);overflow:hidden">
        <tr>
          <td style="background:linear-gradient(135deg,#22b8c2,#0c5561);padding:28px 32px">
            <table cellpadding="0" cellspacing="0" style="border:0">
              <tr>
                <td style="vertical-align:middle;padding-left:12px">
                  <svg width="46" height="46" viewBox="0 0 38 38" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="19" cy="19" r="18.5" fill="#1aa8b2"/>
                    <rect x="7" y="23" width="5" height="8" rx="2.5" fill="rgba(255,255,255,0.5)"/>
                    <rect x="14" y="18" width="5" height="13" rx="2.5" fill="rgba(255,255,255,0.7)"/>
                    <rect x="21" y="15" width="5" height="16" rx="2.5" fill="rgba(255,255,255,0.88)"/>
                    <rect x="28" y="20" width="4" height="11" rx="2" fill="rgba(255,255,255,0.6)"/>
                    <circle cx="19" cy="10" r="5.5" fill="rgba(255,228,100,0.92)"/>
                    <text x="19" y="10" text-anchor="middle" dominant-baseline="central" font-size="7" font-weight="bold" fill="#0c4a50" font-family="Arial,sans-serif">&#x20AA;</text>
                  </svg>
                </td>
                <td style="vertical-align:middle;padding-right:12px">
                  <h1 style="color:#fff;margin:0;font-size:1.4rem">מעקב הלוואות</h1>
                  <p style="color:rgba(255,255,255,.8);margin:4px 0 0;font-size:.9rem">{label}</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:32px">
            <p style="color:#244349;font-size:1rem;margin:0 0 24px">שלום,<br>קוד האימות שלך לצורך <strong>{label}</strong> הוא:</p>
            <div style="background:#f0fafa;border:2px dashed #22b8c2;border-radius:12px;padding:20px;text-align:center;margin-bottom:24px">
              <span style="font-size:2.4rem;font-weight:700;letter-spacing:.3em;color:#0c5561;font-family:monospace">{otp_code}</span>
            </div>
            <p style="color:#62757b;font-size:.88rem;margin:0">
              הקוד תקף ל-10 דקות בלבד.<br>
              אם לא ביקשת קוד זה, אפשר להתעלם מהמייל הזה.
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f4f8fa;padding:16px 32px;text-align:center">
            <p style="color:#aaa;font-size:.8rem;margin:0">מעקב הלוואות &mdash; נשלח אוטומטית</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


async def send_otp_email(to_email: str, otp_code: str, purpose: str = "login") -> Optional[str]:
    """
    Send OTP email via Brevo HTTP API.
    Falls back to console log when Brevo is not configured (development mode).
    Returns the OTP code itself in dev mode (so the API can expose it to the UI).
    """
    label = _PURPOSE_LABELS.get(purpose, "אימות")

    if not settings.brevo_api_key or not settings.email_from:
        # Not configured — log to console for local dev visibility
        logger.warning(
            "[EMAIL DEV FALLBACK] To: %s | Purpose: %s | OTP: %s",
            to_email,
            purpose,
            otp_code,
        )
        print(f"\n{'='*50}")
        print(f"[OTP DEV] Email: {to_email}  |  Purpose: {purpose}  |  Code: {otp_code}")
        print(f"{'='*50}\n")
        return otp_code if settings.debug else None

    payload = {
        "sender": {"name": settings.email_from_name, "email": settings.email_from},
        "to": [{"email": to_email}],
        "subject": f"קוד אימות ({label}) — מעקב הלוואות",
        "htmlContent": _build_html(otp_code, purpose),
        "textContent": f"קוד האימות שלך: {otp_code}\nהקוד תקף ל-10 דקות.",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                _BREVO_API_URL,
                json=payload,
                headers={
                    "api-key": settings.brevo_api_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
        return None
    except Exception as exc:
        logger.error("[EMAIL ERROR] Failed to send OTP email to %s: %s", to_email, exc)
        return None

