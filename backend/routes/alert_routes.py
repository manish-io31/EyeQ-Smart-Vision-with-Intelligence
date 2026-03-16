"""
EYEQ – Alert Routes

GET /alerts            – paginated alert history
GET /alerts/{id}       – single alert detail
GET /detection-log     – alias for /alerts (dashboard-friendly)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database.db import get_db
from backend.routes.auth_routes import get_current_user
from backend.services import alert_service

router = APIRouter(tags=["Alerts"])


class AlertResponse(BaseModel):
    id: int
    detection_label: str
    confidence: Optional[float]
    camera_source: Optional[str]
    image_path: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


@router.get("/alerts", response_model=list[AlertResponse])
def get_alerts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return alert_service.get_alerts(db, limit=limit, offset=offset)


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    alert = alert_service.get_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert


# Dashboard-friendly alias
@router.get("/detection-log", response_model=list[AlertResponse])
def detection_log(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return alert_service.get_alerts(db, limit=limit)
