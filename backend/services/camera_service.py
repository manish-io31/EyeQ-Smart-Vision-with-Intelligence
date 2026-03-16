"""
EYEQ – Camera Service

CRUD operations for cameras stored in the database.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.camera_model import Camera
from utils.helpers import get_logger

logger = get_logger(__name__)


def list_cameras(db: Session) -> List[Camera]:
    return db.query(Camera).order_by(Camera.created_at.desc()).all()


def get_camera(db: Session, camera_id: int) -> Optional[Camera]:
    return db.query(Camera).filter(Camera.id == camera_id).first()


def add_camera(db: Session, name: str, source: str) -> Camera:
    cam = Camera(camera_name=name, camera_source=source)
    db.add(cam)
    db.commit()
    db.refresh(cam)
    logger.info("Camera added: %s => %s", name, source)
    return cam


def delete_camera(db: Session, camera_id: int) -> bool:
    cam = get_camera(db, camera_id)
    if not cam:
        return False
    db.delete(cam)
    db.commit()
    logger.info("Camera deleted: id=%d", camera_id)
    return True


def set_camera_active(db: Session, camera_id: int, active: bool) -> Optional[Camera]:
    cam = get_camera(db, camera_id)
    if not cam:
        return None
    cam.is_active = active
    db.commit()
    db.refresh(cam)
    return cam
