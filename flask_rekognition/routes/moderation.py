"""
Image & Video Moderation Blueprint

GET  /moderation        — render page (age-gated)
POST /verify-age        — verify DOB, store result in session
POST /moderate-image    — detect_moderation_labels() on uploaded image
POST /moderate-video    — frame-by-frame OR S3 async video moderation
"""

import logging
import os
import tempfile
import time
from datetime import date, datetime

import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, render_template, session
from flask_login import login_required, current_user

import config

moderation_bp = Blueprint("moderation", __name__)
logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE     = 5   * 1024 * 1024   # 5 MB
MAX_VIDEO_SIZE     = 100 * 1024 * 1024   # 100 MB
ALLOWED_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

# Substrings that classify a label as unsafe
UNSAFE_TERMS = {
    "nudity", "explicit", "violence", "graphic", "sexual",
    "suggestive", "hate", "weapon", "drug", "tobacco", "alcohol",
    "gambling", "self-harm", "disturbing", "unsafe",
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _rekognition_client():
    if not config.AWS_ACCESS_KEY_ID:
        return None
    try:
        return boto3.client(
            "rekognition",
            aws_access_key_id     = config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = config.AWS_SECRET_ACCESS_KEY,
            region_name           = config.AWS_REGION,
        )
    except Exception as e:
        logger.error("Rekognition client error: %s", e)
        return None


def _classify(name: str, confidence: float) -> dict:
    norm = name.lower()
    is_unsafe = any(t in norm for t in UNSAFE_TERMS)
    return {
        "name":       name,
        "confidence": round(confidence, 2),
        "status":     "Unsafe" if is_unsafe else "Safe",
        "is_unsafe":  is_unsafe,
    }


def _demo_labels() -> list:
    return [{"name": "AWS Rekognition not configured — demo mode",
             "confidence": 0.0, "status": "Safe", "is_unsafe": False}]


# ── Routes ────────────────────────────────────────────────────────────────────

@moderation_bp.route("/moderation")
@login_required
def index():
    return render_template(
        "moderation.html",
        user         = current_user,
        age_verified = session.get("age_verified", False),
    )


@moderation_bp.route("/verify-age", methods=["POST"])
@login_required
def verify_age():
    data    = request.get_json(silent=True) or {}
    dob_str = (data.get("dob") or "").strip()

    if not dob_str:
        return jsonify({"error": "Date of birth is required"}), 400

    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format — use YYYY-MM-DD"}), 400

    today = date.today()
    if dob >= today:
        return jsonify({"verified": False,
                        "message": "Invalid date of birth."}), 400

    age = (today.year - dob.year
           - ((today.month, today.day) < (dob.month, dob.day)))

    if age >= 18:
        session["age_verified"] = True
        session.permanent = True
        return jsonify({"verified": True, "age": age})
    else:
        session["age_verified"] = False
        return jsonify({
            "verified": False,
            "age":      age,
            "message":  "Access restricted: You must be 18+ to access this content.",
        })


@moderation_bp.route("/moderate-image", methods=["POST"])
@login_required
def moderate_image():
    if not session.get("age_verified"):
        return jsonify({"error": "Age verification required"}), 403

    f = request.files.get("image")
    if not f or not f.filename:
        return jsonify({"error": "No image uploaded"}), 400
    if not f.content_type.startswith("image/"):
        return jsonify({"error": "File must be a JPEG or PNG image"}), 400

    data = f.read()
    if len(data) > MAX_IMAGE_SIZE:
        return jsonify({"error": "Image too large — max 5 MB"}), 413

    client = _rekognition_client()
    if not client:
        return jsonify({"labels": _demo_labels(), "is_unsafe": False,
                        "count": 1, "mode": "demo"})

    try:
        resp = client.detect_moderation_labels(
            Image={"Bytes": data}, MinConfidence=50
        )
    except ClientError as e:
        logger.error("detect_moderation_labels: %s", e)
        return jsonify({"error": str(e)}), 500

    raw = resp.get("ModerationLabels", [])
    labels = [_classify(l["Name"], l["Confidence"]) for l in raw]

    if not labels:
        labels = [{"name": "No moderation issues detected",
                   "confidence": 100.0, "status": "Safe", "is_unsafe": False}]

    return jsonify({
        "labels":    labels,
        "is_unsafe": any(l["is_unsafe"] for l in labels),
        "count":     len(labels),
        "mode":      "rekognition",
    })


@moderation_bp.route("/moderate-video", methods=["POST"])
@login_required
def moderate_video():
    if not session.get("age_verified"):
        return jsonify({"error": "Age verification required"}), 403

    f = request.files.get("video")
    if not f or not f.filename:
        return jsonify({"error": "No video uploaded"}), 400

    filename = secure_filename(f.filename)
    ext      = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTS:
        return jsonify({"error": f"Unsupported format. Allowed: {', '.join(ALLOWED_VIDEO_EXTS)}"}), 400

    data = f.read()
    if len(data) > MAX_VIDEO_SIZE:
        return jsonify({"error": "Video too large — max 100 MB"}), 413

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        tmp.write(data)
        tmp.flush()
        tmp.close()

        if getattr(config, "AWS_S3_BUCKET", ""):
            labels, mode = _moderate_video_s3(tmp.name, filename), "rekognition-video"
        else:
            labels, mode = _moderate_video_frames(tmp.name), "frames"
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    if not labels:
        labels = [{"name": "No moderation issues detected",
                   "confidence": 100.0, "status": "Safe", "is_unsafe": False}]

    return jsonify({
        "labels":    labels,
        "is_unsafe": any(l["is_unsafe"] for l in labels),
        "count":     len(labels),
        "mode":      mode,
    })


# ── Video helpers ─────────────────────────────────────────────────────────────

def _moderate_video_frames(video_path: str) -> list:
    """Sample ~10 key frames and run image moderation on each."""
    client = _rekognition_client()
    if not client:
        return _demo_labels()

    try:
        import cv2
    except ImportError:
        return [{"name": "OpenCV unavailable for frame extraction",
                 "confidence": 0.0, "status": "Safe", "is_unsafe": False}]

    cap    = cv2.VideoCapture(video_path)
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    step   = max(1, total // 10)
    label_map: dict[str, float] = {}

    try:
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if idx % step == 0:
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    try:
                        r = client.detect_moderation_labels(
                            Image={"Bytes": buf.tobytes()}, MinConfidence=50
                        )
                        for lbl in r.get("ModerationLabels", []):
                            n, c = lbl["Name"], lbl["Confidence"]
                            if n not in label_map or c > label_map[n]:
                                label_map[n] = c
                    except ClientError:
                        pass
            idx += 1
    finally:
        cap.release()

    return [_classify(n, c) for n, c in sorted(label_map.items(), key=lambda x: -x[1])]


def _moderate_video_s3(video_path: str, filename: str) -> list:
    """Upload to S3, run async Rekognition content moderation, delete from S3."""
    bucket  = config.AWS_S3_BUCKET
    s3_key  = f"moderation-tmp/{int(time.time())}_{filename}"

    s3 = boto3.client(
        "s3",
        aws_access_key_id     = config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key = config.AWS_SECRET_ACCESS_KEY,
        region_name           = config.AWS_REGION,
    )
    try:
        s3.upload_file(video_path, bucket, s3_key)
    except ClientError as e:
        logger.error("S3 upload failed — falling back to frames: %s", e)
        return _moderate_video_frames(video_path)

    client = _rekognition_client()
    try:
        resp   = client.start_content_moderation(
            Video      = {"S3Object": {"Bucket": bucket, "Name": s3_key}},
            MinConfidence = 50,
        )
        job_id = resp["JobId"]

        # Poll up to 2 minutes
        result = None
        for _ in range(24):
            time.sleep(5)
            result = client.get_content_moderation(JobId=job_id)
            if result["JobStatus"] in ("SUCCEEDED", "FAILED"):
                break

        if not result or result["JobStatus"] != "SUCCEEDED":
            return _moderate_video_frames(video_path)

        label_map: dict[str, float] = {}
        for item in result.get("ModerationLabels", []):
            lbl = item.get("ModerationLabel", {})
            n, c = lbl.get("Name", ""), lbl.get("Confidence", 0.0)
            if n and (n not in label_map or c > label_map[n]):
                label_map[n] = c

        return [_classify(n, c) for n, c in sorted(label_map.items(), key=lambda x: -x[1])]

    except ClientError as e:
        logger.error("Video moderation job failed: %s", e)
        return _moderate_video_frames(video_path)
    finally:
        try:
            s3.delete_object(Bucket=bucket, Key=s3_key)
        except Exception:
            pass
