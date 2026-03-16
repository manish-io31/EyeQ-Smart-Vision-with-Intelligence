"""
EYEQ – Email Alert Module (SMTP)

Sends an email notification (with optional screenshot attachment)
to the admin address whenever a suspicious event is detected.
"""

import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from utils.helpers import get_logger, utc_now_str
from config.settings import (
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    SMTP_HOST,
    SMTP_PORT,
    ADMIN_EMAIL,
)

logger = get_logger(__name__)


def send_email_alert(
    label: str,
    confidence: float = 0.0,
    camera_source: str = "",
    image_path: str = "",
) -> bool:
    """
    Send an email alert via SMTP (TLS).

    Args:
        label:         Detected object label.
        confidence:    Model confidence score.
        camera_source: Camera identifier.
        image_path:    Optional path to the alert screenshot to attach.

    Returns:
        True if the email was dispatched successfully, False otherwise.
    """
    if not all([EMAIL_ADDRESS, EMAIL_PASSWORD, ADMIN_EMAIL]):
        logger.warning("Email credentials not configured. Email alert skipped.")
        return False

    timestamp = utc_now_str()
    subject = f"⚠ EYEQ ALERT – {label} detected"

    # ── HTML body ──────────────────────────────────────────────
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;padding:20px;background:#f4f4f4;">
      <div style="background:#fff;border-left:6px solid #e53935;padding:20px;border-radius:6px;">
        <h2 style="color:#e53935;">⚠ EYEQ Security Alert</h2>
        <table style="border-collapse:collapse;width:100%;">
          <tr><td style="padding:8px;font-weight:bold;">Timestamp</td><td style="padding:8px;">{timestamp}</td></tr>
          <tr style="background:#f9f9f9;"><td style="padding:8px;font-weight:bold;">Detection</td><td style="padding:8px;">{label}</td></tr>
          <tr><td style="padding:8px;font-weight:bold;">Confidence</td><td style="padding:8px;">{confidence:.0%}</td></tr>
          <tr style="background:#f9f9f9;"><td style="padding:8px;font-weight:bold;">Camera</td><td style="padding:8px;">{camera_source or 'Unknown'}</td></tr>
        </table>
        <p style="margin-top:20px;color:#555;">
          Suspicious activity was detected by EYEQ. Please review the attached screenshot
          and log into the EYEQ dashboard to investigate.
        </p>
        <p style="color:#999;font-size:12px;">This is an automated message from EYEQ – Intelligent Vision Security System.</p>
      </div>
    </body></html>
    """

    # ── Assemble MIME message ──────────────────────────────────
    msg = MIMEMultipart("related")
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ADMIN_EMAIL
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    # Attach screenshot if available
    if image_path and os.path.isfile(image_path):
        try:
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()
            image = MIMEImage(img_data, name=os.path.basename(image_path))
            image.add_header("Content-Disposition", "attachment", filename=os.path.basename(image_path))
            msg.attach(image)
        except Exception as attach_exc:
            logger.warning("Could not attach screenshot: %s", attach_exc)

    # ── Send via SMTP TLS ──────────────────────────────────────
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, ADMIN_EMAIL, msg.as_string())
        logger.info("Email alert sent to %s for label: %s", ADMIN_EMAIL, label)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check EMAIL_ADDRESS and EMAIL_PASSWORD in .env")
    except smtplib.SMTPException as smtp_exc:
        logger.error("SMTP error: %s", smtp_exc)
    except Exception as exc:
        logger.error("Unexpected email error: %s", exc)

    return False
