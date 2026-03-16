"""
Detection Service — tries AWS Rekognition first, falls back to YOLOv8

Priority:
  1. AWS Rekognition (if credentials set)  →  cloud, all 4 APIs
  2. YOLOv8 / ultralytics  (if installed)  →  local, 80 COCO classes
  3. Demo mode                             →  fake bounding boxes

All methods return a unified list:
  [{ label, confidence, detection_type, bounding_box, color, is_alert }]
  bounding_box = { Left, Top, Width, Height }   (0-1 fractions of image size)
"""

import base64
import logging
import os
from typing import List, Optional

import config

logger = logging.getLogger(__name__)

# ─── Color map ─────────────────────────────────────────────────
COLORS = {
    "person":     "#FF6B00",
    "face":       "#00B4FF",
    "text":       "#00E676",
    "moderation": "#FF0000",
    "car":        "#FFD600", "truck": "#FFD600", "bus": "#FFD600",
    "motorcycle": "#FFAB00", "bicycle": "#FF6F00",
    "cell phone": "#CE93D8", "laptop": "#BA68C8", "tv": "#9C27B0",
    "backpack":   "#26C6DA", "suitcase": "#00ACC1",
    "knife":      "#FF0000", "gun": "#FF0000", "scissors": "#FF1744",
    "fire":       "#FF6D00", "smoke": "#B0BEC5",
    "dog":        "#66BB6A", "cat": "#43A047", "bird": "#2E7D32",
    "default":    "#00E676",
}

THREAT_LABELS = {
    "person", "knife", "gun", "pistol", "rifle", "weapon", "scissors",
    "fire", "smoke", "mask", "cell phone", "laptop", "backpack",
    "car", "motorcycle", "truck", "bus",
}


def _color(label: str, dtype: str) -> str:
    if dtype == "face":       return COLORS["face"]
    if dtype == "text":       return COLORS["text"]
    if dtype == "moderation": return COLORS["moderation"]
    return COLORS.get(label.lower(), COLORS["default"])


def _is_alert(label: str, confidence: float) -> bool:
    return (label.lower() in THREAT_LABELS
            and confidence >= config.ALERT_CONFIDENCE_THRESHOLD)


# ══════════════════════════════════════════════════════════════
# AWS Rekognition
# ══════════════════════════════════════════════════════════════

try:
    import boto3
    from botocore.exceptions import ClientError
    _BOTO3 = True
except ImportError:
    _BOTO3 = False


class _RekognitionBackend:
    def __init__(self):
        self.available = False
        self._client   = None
        if not _BOTO3:
            return
        if not config.AWS_ACCESS_KEY_ID:
            return
        try:
            self._client = boto3.client(
                "rekognition",
                aws_access_key_id     = config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key = config.AWS_SECRET_ACCESS_KEY,
                region_name           = config.AWS_REGION,
            )
            self._client.list_collections(MaxResults=1)
            self.available = True
            logger.info("AWS Rekognition ready (region: %s)", config.AWS_REGION)
        except Exception as e:
            logger.warning("Rekognition init failed: %s", e)

    def detect(self, image_bytes: bytes) -> List[dict]:
        results = []
        results.extend(self._labels(image_bytes))
        results.extend(self._faces(image_bytes))
        results.extend(self._text(image_bytes))
        results.extend(self._moderation(image_bytes))
        return results

    def _labels(self, image_bytes):
        try:
            r = self._client.detect_labels(
                Image={"Bytes": image_bytes},
                MaxLabels=50,
                MinConfidence=config.DETECTION_CONFIDENCE_THRESHOLD,
            )
        except ClientError as e:
            logger.error("detect_labels: %s", e); return []

        out = []
        for lbl in r.get("Labels", []):
            name, conf = lbl["Name"], lbl["Confidence"]
            instances  = lbl.get("Instances", [])
            if instances:
                for inst in instances:
                    bb = inst.get("BoundingBox")
                    out.append({"label": name, "confidence": conf,
                                "detection_type": "label", "bounding_box": bb,
                                "color": _color(name, "label"),
                                "is_alert": _is_alert(name, conf)})
            else:
                out.append({"label": name, "confidence": conf,
                            "detection_type": "scene", "bounding_box": None,
                            "color": _color(name, "label"),
                            "is_alert": name.lower() in THREAT_LABELS and conf >= 90})
        return out

    def _faces(self, image_bytes):
        try:
            r = self._client.detect_faces(Image={"Bytes": image_bytes}, Attributes=["ALL"])
        except ClientError as e:
            logger.error("detect_faces: %s", e); return []
        out = []
        for face in r.get("FaceDetails", []):
            conf = face["Confidence"]
            bb   = face.get("BoundingBox")
            emotions = face.get("Emotions", [])
            top_emo  = max(emotions, key=lambda e: e["Confidence"])["Type"] if emotions else "Unknown"
            age = face.get("AgeRange", {})
            label = f"Face ({top_emo}, age {age.get('Low',0)}-{age.get('High',99)})"
            out.append({"label": label, "confidence": conf,
                        "detection_type": "face", "bounding_box": bb,
                        "color": COLORS["face"], "is_alert": False})
        return out

    def _text(self, image_bytes):
        try:
            r = self._client.detect_text(Image={"Bytes": image_bytes})
        except ClientError as e:
            logger.error("detect_text: %s", e); return []
        out = []
        for t in r.get("TextDetections", []):
            if t["Type"] != "LINE": continue
            conf = t["Confidence"]
            if conf < config.DETECTION_CONFIDENCE_THRESHOLD: continue
            bb = t.get("Geometry", {}).get("BoundingBox")
            out.append({"label": f'Text: "{t["DetectedText"]}"', "confidence": conf,
                        "detection_type": "text", "bounding_box": bb,
                        "color": COLORS["text"], "is_alert": False})
        return out

    def _moderation(self, image_bytes):
        try:
            r = self._client.detect_moderation_labels(
                Image={"Bytes": image_bytes},
                MinConfidence=config.DETECTION_CONFIDENCE_THRESHOLD)
        except ClientError as e:
            logger.error("detect_moderation: %s", e); return []
        out = []
        for lbl in r.get("ModerationLabels", []):
            out.append({"label": f"UNSAFE: {lbl['Name']}", "confidence": lbl["Confidence"],
                        "detection_type": "moderation", "bounding_box": None,
                        "color": COLORS["moderation"], "is_alert": True})
        return out


# ══════════════════════════════════════════════════════════════
# YOLOv8 Fallback
# ══════════════════════════════════════════════════════════════

try:
    from ultralytics import YOLO as _YOLO
    import cv2 as _cv2
    import numpy as _np
    _YOLO_PKG = True
except ImportError:
    _YOLO_PKG = False


class _YoloBackend:
    def __init__(self):
        self.available = False
        self._model    = None
        if not _YOLO_PKG:
            logger.warning("ultralytics not installed. YOLO fallback unavailable.")
            return
        model_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), config.YOLO_MODEL_PATH)
        )
        try:
            self._model   = _YOLO(model_path)
            self.available = True
            logger.info("YOLOv8 fallback loaded: %s", model_path)
        except Exception as e:
            logger.warning("YOLO load failed: %s — will use demo mode", e)

    def detect(self, image_bytes: bytes) -> List[dict]:
        """Run YOLOv8 on raw JPEG bytes, return unified detection list."""
        if not self.available:
            return []

        # Decode bytes → OpenCV BGR frame
        nparr  = _np.frombuffer(image_bytes, _np.uint8)
        frame  = _cv2.imdecode(nparr, _cv2.IMREAD_COLOR)
        if frame is None:
            return []
        h, w = frame.shape[:2]

        try:
            results = self._model(frame, conf=config.DETECTION_CONFIDENCE_THRESHOLD / 100,
                                  verbose=False)
        except Exception as e:
            logger.error("YOLO inference: %s", e)
            return []

        out = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf   = float(box.conf[0]) * 100      # 0-100
                cls_id = int(box.cls[0])
                label  = result.names.get(cls_id, "unknown")

                # Normalise bbox to 0-1 fractions (same format as Rekognition)
                bb = {
                    "Left":   x1 / w,
                    "Top":    y1 / h,
                    "Width":  (x2 - x1) / w,
                    "Height": (y2 - y1) / h,
                }
                out.append({
                    "label":          label,
                    "confidence":     conf,
                    "detection_type": "yolo",
                    "bounding_box":   bb,
                    "color":          _color(label, "yolo"),
                    "is_alert":       _is_alert(label, conf),
                })
        return out


# ══════════════════════════════════════════════════════════════
# Demo mode (no AWS, no YOLO)
# ══════════════════════════════════════════════════════════════

def _demo() -> List[dict]:
    return [
        {"label": "Person (DEMO)", "confidence": 92.5, "detection_type": "demo",
         "bounding_box": {"Left": 0.20, "Top": 0.10, "Width": 0.35, "Height": 0.70},
         "color": COLORS["person"], "is_alert": True},
        {"label": "Cell Phone (DEMO)", "confidence": 78.3, "detection_type": "demo",
         "bounding_box": {"Left": 0.60, "Top": 0.55, "Width": 0.15, "Height": 0.25},
         "color": COLORS["cell phone"], "is_alert": False},
    ]


# ══════════════════════════════════════════════════════════════
# Unified Detector — picks best backend
# ══════════════════════════════════════════════════════════════

class DetectionService:
    def __init__(self):
        self._rekognition = _RekognitionBackend()
        self._yolo        = _YoloBackend()

        if self._rekognition.available:
            self.mode = "rekognition"
        elif self._yolo.available:
            self.mode = "yolo"
        else:
            self.mode = "demo"

        logger.info("Detection mode: %s", self.mode)

    @property
    def available(self):
        return self.mode != "demo"

    def detect_all(self, image_bytes: bytes) -> List[dict]:
        if self.mode == "rekognition":
            dets = self._rekognition.detect(image_bytes)
        elif self.mode == "yolo":
            dets = self._yolo.detect(image_bytes)
        else:
            dets = _demo()

        # Sort: alerts first, then by confidence desc
        return sorted(dets, key=lambda d: (-int(d["is_alert"]), -d["confidence"]))


# Module-level singleton
detector = DetectionService()
