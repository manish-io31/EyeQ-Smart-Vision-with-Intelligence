"""
EYEQ – Alert ORM Model
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Float

from backend.database.db import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    detection_label = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=True)
    camera_source = Column(String(255), nullable=True)
    image_path = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f"<Alert id={self.id} label={self.detection_label} ts={self.timestamp}>"
