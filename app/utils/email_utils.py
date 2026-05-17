import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)

_PURPOSE_LABELS = {
    "register": "רישום חשבון",
    "login": "כניסה לחשבון",
    "reset": "איפוס גישה",
}


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
            <h1 style="color:#fff;margin:0;font-size:1.4rem">מעקב הלוואות &#8362;</h1>
            <p style="color:rgba(255,255,255,.8);margin:4px 0 0;font-size:.9rem">{label}</p>
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
    Send OTP email via SMTP.
    Falls back to console log when SMTP is not configured (development mode).
    Returns the OTP code itself in dev mode (so the API can expose it to the UI).
    """
    label = _PURPOSE_LABELS.get(purpose, "אימות")

    if not settings.smtp_host or not settings.smtp_user:
        # Development fallback — print to console and return code for UI display
        logger.warning(
            "[EMAIL DEV FALLBACK] To: %s | Purpose: %s | OTP: %s",
            to_email,
            purpose,
            otp_code,
        )
        print(f"\n{'='*50}")
        print(f"[OTP DEV] Email: {to_email}  |  Purpose: {purpose}  |  Code: {otp_code}")
        print(f"{'='*50}\n")
        return otp_code

    message = MIMEMultipart("alternative")
    message["Subject"] = f"קוד אימות ({label}) — מעקב הלוואות"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from or settings.smtp_user}>"
    message["To"] = to_email

    plain = f"קוד האימות שלך: {otp_code}\nהקוד תקף ל-10 דקות."
    message.attach(MIMEText(plain, "plain", "utf-8"))
    message.attach(MIMEText(_build_html(otp_code, purpose), "html", "utf-8"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        return None
    except Exception as exc:
        logger.error("[EMAIL ERROR] Failed to send OTP email to %s: %s", to_email, exc)
        # Return the code so the caller can expose it in dev_code (visible in logs/response)
        return otp_code
