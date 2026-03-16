"""
EYEQ – Alert DB Service

Persists detection alerts and retrieves alert history.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.alert_model import Alert
from utils.helpers import get_logger

logger = get_logger(__name__)


def log_alert(
    db: Session,
    detection_label: str,
    confidence: float = 0.0,
    camera_source: str = "",
    image_path: str = "",
) -> Alert:
    """Persist a new alert record."""
    alert = Alert(
        detection_label=detection_label,
        confidence=round(confidence, 4),
        camera_source=camera_source,
        image_path=image_path,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    logger.info("Alert logged: label=%s confidence=%.2f", detection_label, confidence)
    return alert


def get_alerts(db: Session, limit: int = 100, offset: int = 0) -> List[Alert]:
    return (
        db.query(Alert)
        .order_by(Alert.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_alert(db: Session, alert_id: int) -> Optional[Alert]:
    return db.query(Alert).filter(Alert.id == alert_id).first()


def count_alerts(db: Session) -> int:
    return db.query(Alert).count()
