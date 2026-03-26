"""Alerts Blueprint"""

from flask import Blueprint, render_template, jsonify, request, abort
from flask_login import login_required, current_user
from models import db, AlertEvent

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts")
@login_required
def index():
    return render_template("alerts.html", user=current_user)


@alerts_bp.route("/api/alerts")
@login_required
def list_alerts():
    page     = request.args.get("page",     1,   type=int)
    per_page = min(request.args.get("per_page", 25, type=int), 100)
    label_f  = request.args.get("label",    "",  type=str).strip()
    min_conf = request.args.get("min_confidence", 0.0, type=float)

    q = AlertEvent.query
    if label_f:
        q = q.filter(AlertEvent.object_detected.ilike(f"%{label_f}%"))
    if min_conf > 0:
        q = q.filter(AlertEvent.confidence_score >= min_conf)

    p = q.order_by(AlertEvent.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    return jsonify({
        "alerts":   [a.to_dict() for a in p.items],
        "total":    p.total,
        "pages":    p.pages,
        "page":     page,
    })


@alerts_bp.route("/api/alerts/<int:aid>")
@login_required
def get_alert(aid):
    return jsonify(AlertEvent.query.get_or_404(aid).to_dict())


@alerts_bp.route("/api/alerts/<int:aid>", methods=["DELETE"])
@login_required
def delete_alert(aid):
    if not current_user.is_admin():
        abort(403)
    a = AlertEvent.query.get_or_404(aid)
    db.session.delete(a)
    db.session.commit()
    return jsonify({"deleted": True})


@alerts_bp.route("/api/alerts/summary")
@login_required
def summary():
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    count = AlertEvent.query.filter(
        AlertEvent.timestamp >= now - timedelta(minutes=5)).count()
    return jsonify({"new_alerts": count})
