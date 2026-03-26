"""
Image Detection Blueprint
GET  /image-detection   — render page
POST /detect-image      — upload image → run detection → return JSON
"""

import logging

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

from services.rekognition_service import detector
import config

detection_bp = Blueprint("detection", __name__)
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 5 * 1024 * 1024   # 5 MB

# Labels considered safe / expected in everyday scenes.
# Anything NOT in this set is flagged as Miscellaneous / Potential Threat.
SAFE_LABELS = {
    "person", "people", "man", "woman", "child", "human",
    "car", "vehicle", "truck", "bus", "motorcycle", "bicycle",
    "building", "house", "architecture", "road", "street", "path",
    "tree", "plant", "flower", "grass", "sky", "cloud", "water",
    "chair", "table", "desk", "door", "window", "floor", "wall", "ceiling",
    "dog", "cat", "bird", "animal",
    "sign", "light", "lamp", "furniture", "clothing", "shoe",
    "aircraft", "airplane", "airport", "transportation",
    "wheel", "airfield", "airliner", "machine", "text",
    "food", "drink", "bottle", "cup",
}


@detection_bp.route("/image-detection")
@login_required
def index():
    return render_template("image_detection.html", user=current_user)


@detection_bp.route("/detect-image", methods=["POST"])
@login_required
def detect_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    f = request.files["image"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not f.content_type.startswith("image/"):
        return jsonify({"error": "File must be an image (JPEG or PNG)"}), 400

    image_bytes = f.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": "Image too large — max 5 MB"}), 413

    try:
        raw = detector.detect_all(image_bytes)
    except Exception as e:
        logger.error("Image detection failed: %s", e)
        return jsonify({"error": str(e)}), 500

    labels = []
    alert_triggered = False

    for det in raw:
        name       = det["label"]
        confidence = det["confidence"]
        norm       = name.lower().split(" (")[0].strip()

        # Safe-list check: if no safe word appears in the normalised label → misc
        in_safe = any(s in norm for s in SAFE_LABELS)
        is_misc = not in_safe

        # Threat = known HIGH_THREAT label  OR  miscellaneous above alert threshold
        is_threat = det.get("is_alert", False) or (
            is_misc and confidence >= config.ALERT_CONFIDENCE_THRESHOLD
        )

        if is_threat:
            alert_triggered = True

        labels.append({
            "name":           name,
            "confidence":     round(confidence, 2),
            "is_threat":      is_threat,
            "is_misc":        is_misc,
            "detection_type": det.get("detection_type", "unknown"),
        })

    return jsonify({
        "labels":          labels,
        "alert_triggered": alert_triggered,
        "detection_mode":  detector.mode,
        "count":           len(labels),
    })
