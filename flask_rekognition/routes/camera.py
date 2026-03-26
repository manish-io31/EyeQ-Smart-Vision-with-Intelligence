"""
Camera / Detection Blueprint
POST /api/detect  — receive base64 frame → detect all objects → save DB → fire alerts
GET  /api/status  — service health
POST /api/snapshot — save frame without detection
GET  /api/rtsp/feed — threaded MJPEG stream from RTSP/OpenCV source
"""

import base64
import json
import logging
import os
import queue as _queue
import threading
from datetime import datetime

import cv2
from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_login import login_required, current_user

from models import db, AlertEvent, DetectionLog
from services.rekognition_service import detector
from services.alert_service import dispatch_alert, _cooldown_ok, _update
import config

camera_bp = Blueprint("camera", __name__)
logger    = logging.getLogger(__name__)

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


@camera_bp.route("/api/detect", methods=["POST"])
@login_required
def detect():
    """
    Receive JPEG frame as base64, run all detections, return JSON bounding boxes.
    """
    data = request.get_json(silent=True)
    if not data or "frame" not in data:
        return jsonify({"error": "Missing 'frame'"}), 400

    camera_source = data.get("camera_source", "webcam")

    # Decode base64
    try:
        frame_b64 = data["frame"]
        if "," in frame_b64:
            frame_b64 = frame_b64.split(",", 1)[1]
        image_bytes = base64.b64decode(frame_b64)
    except Exception as e:
        return jsonify({"error": f"Bad base64: {e}"}), 400

    # Run detection
    try:
        detections = detector.detect_all(image_bytes)
    except Exception as e:
        logger.error("Detection failed: %s", e)
        return jsonify({"error": str(e)}), 500

    alert_triggered = False
    snapshot_path   = None

    for det in detections:
        label      = det["label"]
        confidence = det["confidence"]

        # Log every detection
        log = DetectionLog(
            label          = label,
            confidence     = confidence,
            detection_type = det.get("detection_type", "yolo"),
            bounding_box   = json.dumps(det["bounding_box"]) if det.get("bounding_box") else None,
            camera_source  = camera_source,
        )
        db.session.add(log)

        # Alert on high-confidence threats — gated by per-label cooldown
        if det.get("is_alert") and confidence >= config.ALERT_CONFIDENCE_THRESHOLD:
            alert_triggered = True

            # Only write to DB and dispatch if cooldown has elapsed for this label
            if _cooldown_ok(label):
                _update(label)   # mark cooldown start before async dispatch

                if snapshot_path is None:
                    snapshot_path = _save_snapshot(image_bytes, label)

                event = AlertEvent(
                    object_detected  = label,
                    confidence_score = confidence,
                    detection_type   = det.get("detection_type", "yolo"),
                    camera_source    = camera_source,
                    image_path       = snapshot_path,
                    alert_sent       = True,
                    sms_sent         = bool(config.TWILIO_ACCOUNT_SID),
                )
                db.session.add(event)

                # ★ Send SMS + email in background
                dispatch_alert(
                    label      = label,
                    confidence = confidence,
                    camera     = camera_source,
                    image_path = snapshot_path,
                )

    db.session.commit()

    return jsonify({
        "detections":      detections,
        "alert_triggered": alert_triggered,
        "detection_mode":  detector.mode,
        "count":           len(detections),
    })


@camera_bp.route("/api/status")
@login_required
def status():
    return jsonify({
        "detection_mode":        detector.mode,
        "rekognition_available": detector.mode == "rekognition",
        "yolo_available":        detector.mode == "yolo",
        "confidence_threshold":  config.DETECTION_CONFIDENCE_THRESHOLD,
        "alert_threshold":       config.ALERT_CONFIDENCE_THRESHOLD,
        "admin_phone":           _mask_phone(config.ADMIN_PHONE_NUMBER),
        "sms_configured":        bool(config.TWILIO_ACCOUNT_SID),
    })


@camera_bp.route("/api/snapshot", methods=["POST"])
@login_required
def snapshot():
    data = request.get_json(silent=True)
    if not data or "frame" not in data:
        return jsonify({"error": "Missing frame"}), 400
    try:
        b64 = data["frame"]
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        raw = base64.b64decode(b64)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    path = _save_snapshot(raw, "manual")
    return jsonify({"saved": True, "path": path})


def _save_snapshot(image_bytes: bytes, label: str) -> str:
    ts   = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    name = f"alert_{label.replace(' ', '_')}_{ts}.jpg"
    path = os.path.join(SNAPSHOT_DIR, name)
    try:
        with open(path, "wb") as f:
            f.write(image_bytes)
    except Exception as e:
        logger.error("Snapshot save failed: %s", e)
        return ""
    return path


@camera_bp.route("/api/rtsp/feed")
@login_required
def rtsp_feed():
    """Stream MJPEG frames from an RTSP (or any OpenCV-readable) source."""
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "Missing url parameter"}), 400
    return Response(
        stream_with_context(_gen_rtsp_frames(url)),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ── Threaded capture ────────────────────────────────────────────────────────
class _ThreadedCap:
    """
    Reads frames from an OpenCV source in a background daemon thread so the
    main generator never blocks waiting for a slow camera/network decode.
    The queue is capped at 2 frames — old frames are discarded to keep latency
    low (we always want the newest frame, not a backlog).
    """
    _MAXSIZE = 2

    def __init__(self, url: str):
        self._cap   = cv2.VideoCapture(url)
        self._q     = _queue.Queue(maxsize=self._MAXSIZE)
        self._stop  = threading.Event()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        while not self._stop.is_set():
            ret, frame = self._cap.read()
            if not ret:
                break
            # Drop oldest frame if queue is full so we never accumulate lag
            if self._q.full():
                try:
                    self._q.get_nowait()
                except _queue.Empty:
                    pass
            self._q.put(frame)

    def read(self):
        """Returns (True, frame) or (False, None) on timeout."""
        try:
            return True, self._q.get(timeout=1.0)
        except _queue.Empty:
            return False, None

    def release(self):
        self._stop.set()
        self._cap.release()


_RTSP_FRAME_SKIP = 2   # encode every Nth frame (reduces CPU/bandwidth)
_RTSP_MAX_W      = 640  # resize wider streams to this width


def _gen_rtsp_frames(url: str):
    cap     = _ThreadedCap(url)
    frame_n = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_n += 1
            if frame_n % _RTSP_FRAME_SKIP != 0:
                continue
            # Resize to cap bandwidth without distorting aspect ratio
            h, w = frame.shape[:2]
            if w > _RTSP_MAX_W:
                scale = _RTSP_MAX_W / w
                frame = cv2.resize(
                    frame,
                    (int(w * scale), int(h * scale)),
                    interpolation=cv2.INTER_LINEAR,
                )
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok:
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                   + buf.tobytes() + b"\r\n")
    finally:
        cap.release()


def _mask_phone(phone: str) -> str:
    """Show only last 4 digits for security: +91XXXXXX1234 → +91XXXXXX1234"""
    if not phone or len(phone) < 6:
        return "Not configured"
    return phone[:3] + "****" + phone[-4:]
