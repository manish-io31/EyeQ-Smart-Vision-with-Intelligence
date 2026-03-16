"""Dashboard Blueprint"""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, AlertEvent, DetectionLog
from services.rekognition_service import detector

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    return render_template("dashboard.html", user=current_user)


@dashboard_bp.route("/api/stats")
@login_required
def stats():
    """AJAX endpoint — called every 5 s to refresh dashboard WITHOUT page reload."""
    now = datetime.utcnow()

    total_detections = DetectionLog.query.count()
    total_alerts     = AlertEvent.query.count()
    alerts_today     = AlertEvent.query.filter(
        AlertEvent.timestamp >= now.replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    alerts_last_hour = AlertEvent.query.filter(
        AlertEvent.timestamp >= now - timedelta(hours=1)
    ).count()

    recent_alerts = (AlertEvent.query
                     .order_by(AlertEvent.timestamp.desc()).limit(10).all())

    # Hourly frequency for Chart.js line graph (last 24 h)
    frequency = []
    for h in range(23, -1, -1):
        t0 = now - timedelta(hours=h + 1)
        t1 = now - timedelta(hours=h)
        count = DetectionLog.query.filter(
            DetectionLog.timestamp.between(t0, t1)).count()
        frequency.append({"hour": t0.strftime("%H:00"), "count": count})

    # Top labels for doughnut chart
    top_labels = (db.session.query(DetectionLog.label,
                  func.count(DetectionLog.id).label("count"))
                  .group_by(DetectionLog.label)
                  .order_by(func.count(DetectionLog.id).desc())
                  .limit(10).all())

    recent_dets = (DetectionLog.query
                   .order_by(DetectionLog.timestamp.desc()).limit(20).all())

    return jsonify({
        "summary": {
            "total_detections": total_detections,
            "total_alerts":     total_alerts,
            "alerts_today":     alerts_today,
            "alerts_last_hour": alerts_last_hour,
        },
        "recent_alerts":    [a.to_dict() for a in recent_alerts],
        "frequency":        frequency,
        "top_labels":       [{"label": r.label, "count": r.count} for r in top_labels],
        "recent_detections":[d.to_dict() for d in recent_dets],
        "detection_mode":   detector.mode,
        "server_time":      now.isoformat() + "Z",
    })
