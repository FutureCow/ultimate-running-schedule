"""Simple SMTP email service for password reset emails."""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send a password reset email. Returns True on success, False on failure."""
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP not configured — skipping password reset email")
        return False

    reset_url = f"{settings.APP_URL}/reset-password?token={reset_token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Cadence – Wachtwoord resetten / Reset your password"
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email

    text = f"""Hallo,

Je hebt een wachtwoord-reset aangevraagd voor je Cadence account.
Klik op de link hieronder om je wachtwoord te resetten (geldig 1 uur):

{reset_url}

Als je dit niet hebt aangevraagd, kun je deze e-mail negeren.

---
Hello,

You requested a password reset for your Cadence account.
Click the link below to reset your password (valid for 1 hour):

{reset_url}

If you did not request this, you can safely ignore this email.
"""

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: Inter, system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 32px; border: 1px solid #334155;">
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
      <div style="width: 40px; height: 40px; background: #22c55e; border-radius: 10px; display: flex; align-items: center; justify-content: center;">
        <svg viewBox="0 0 18 18" fill="none" width="22" height="22">
          <rect x="1" y="10" width="3.5" height="7" rx="1.5" fill="white"/>
          <rect x="7" y="3" width="3.5" height="14" rx="1.5" fill="white"/>
          <rect x="13" y="7" width="3.5" height="10" rx="1.5" fill="white"/>
        </svg>
      </div>
      <span style="font-size: 18px; font-weight: 700; color: white;">Cadence</span>
    </div>
    <h2 style="color: white; font-size: 20px; margin: 0 0 8px;">Wachtwoord resetten</h2>
    <p style="color: #94a3b8; font-size: 14px; margin: 0 0 24px;">
      Klik op de knop hieronder om je wachtwoord te resetten. De link is 1 uur geldig.
    </p>
    <a href="{reset_url}"
       style="display: inline-block; background: #22c55e; color: white; font-weight: 600;
              padding: 12px 28px; border-radius: 10px; text-decoration: none; font-size: 14px;">
      Wachtwoord resetten
    </a>
    <p style="color: #475569; font-size: 12px; margin-top: 24px;">
      Als je dit niet hebt aangevraagd, kun je deze e-mail negeren.
    </p>
  </div>
</body>
</html>"""

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        if settings.SMTP_TLS:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM or settings.SMTP_USER, to_email, msg.as_string())
        else:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM or settings.SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {to_email}: {e}")
        return False
