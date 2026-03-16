"""
EYEQ – SMS Alert Module (Twilio)

Sends an SMS notification to the admin phone number
whenever a suspicious detection event is triggered.
"""

from utils.helpers import get_logger, utc_now_str
from config.settings import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    ADMIN_PHONE_NUMBER,
)

logger = get_logger(__name__)


def send_sms_alert(label: str, confidence: float = 0.0, camera_source: str = "") -> bool:
    """
    Send an SMS alert via Twilio.

    Args:
        label:         Detected object label (e.g. "knife").
        confidence:    Model confidence score (0.0–1.0).
        camera_source: Camera identifier for context.

    Returns:
        True if the SMS was sent successfully, False otherwise.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, ADMIN_PHONE_NUMBER]):
        logger.warning("Twilio credentials not configured. SMS skipped.")
        return False

    try:
        from twilio.rest import Client  # lazy import – optional dependency
    except ImportError:
        logger.error("twilio package not installed. Run: pip install twilio")
        return False

    body = (
        f"⚠ ALERT: Suspicious activity detected by EYEQ at {utc_now_str()}\n"
        f"Label    : {label} ({confidence:.0%})\n"
        f"Camera   : {camera_source or 'Unknown'}\n"
        f"Action   : Please check the EYEQ dashboard immediately."
    )

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=ADMIN_PHONE_NUMBER,
        )
        logger.info("SMS sent. SID: %s", message.sid)
        return True
    except Exception as exc:
        logger.error("Failed to send SMS: %s", exc)
        return False
