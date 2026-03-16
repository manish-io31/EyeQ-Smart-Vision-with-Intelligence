"""
EYEQ – Camera ORM Model
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean

from backend.database.db import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    camera_name = Column(String(100), nullable=False)
    camera_source = Column(String(500), nullable=False)   # 0, rtsp://..., /path/to/video
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Camera id={self.id} name={self.camera_name} source={self.camera_source}>"
