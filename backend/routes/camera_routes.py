"""
EYEQ – Camera Routes

GET    /cameras            – list all cameras
POST   /cameras            – add a camera
DELETE /cameras/{id}       – remove a camera
POST   /cameras/{id}/start – start monitoring
POST   /cameras/{id}/stop  – stop monitoring
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.db import get_db
from backend.routes.auth_routes import get_current_user
from backend.services import camera_service

router = APIRouter(prefix="/cameras", tags=["Cameras"])


class CameraCreate(BaseModel):
    camera_name: str
    camera_source: str   # "0", "rtsp://...", "/path/to/file.mp4"


class CameraResponse(BaseModel):
    id: int
    camera_name: str
    camera_source: str
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=list[CameraResponse])
def get_cameras(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return camera_service.list_cameras(db)


@router.post("/", response_model=CameraResponse, status_code=201)
def add_camera(payload: CameraCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return camera_service.add_camera(db, payload.camera_name, payload.camera_source)


@router.delete("/{camera_id}", status_code=204)
def remove_camera(camera_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not camera_service.delete_camera(db, camera_id):
        raise HTTPException(status_code=404, detail="Camera not found.")


@router.post("/{camera_id}/start", response_model=CameraResponse)
def start_monitoring(camera_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    cam = camera_service.set_camera_active(db, camera_id, True)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")
    return cam


@router.post("/{camera_id}/stop", response_model=CameraResponse)
def stop_monitoring(camera_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    cam = camera_service.set_camera_active(db, camera_id, False)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")
    return cam
