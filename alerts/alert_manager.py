"""
EYEQ – Alert Manager

Orchestrates all notification channels (SMS, email) and
persists alerts to the database in a single call.

This is the single entry point used by the detection pipeline.
"""

import threading
from sqlalchemy.orm import Session

from alerts.sms_alert import send_sms_alert
from alerts.email_alert import send_email_alert
from backend.services.alert_service import log_alert
from utils.helpers import get_logger

logger = get_logger(__name__)


def dispatch_alert(
    db: Session,
    label: str,
    confidence: float = 0.0,
    camera_source: str = "",
    image_path: str = "",
    send_sms: bool = True,
    send_email: bool = True,
):
    """
    Persist an alert to the DB and fire notifications in background threads.

    Args:
        db:            SQLAlchemy session.
        label:         Detection label.
        confidence:    YOLO confidence score.
        camera_source: Camera identifier string.
        image_path:    Path to the saved alert screenshot.
        send_sms:      Whether to send an SMS.
        send_email:    Whether to send an email.
    """
    # 1. Persist to database (synchronous – we want this guaranteed)
    try:
        log_alert(db, label, confidence, camera_source, image_path)
    except Exception as db_exc:
        logger.error("Failed to log alert to DB: %s", db_exc)

    # 2. Fire notification channels asynchronously (non-blocking)
    def _notify():
        if send_sms:
            send_sms_alert(label, confidence, camera_source)
        if send_email:
            send_email_alert(label, confidence, camera_source, image_path)

    thread = threading.Thread(target=_notify, daemon=True)
    thread.start()
    logger.info("Alert dispatched: label=%s confidence=%.2f camera=%s", label, confidence, camera_source)
