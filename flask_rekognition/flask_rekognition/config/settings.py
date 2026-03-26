"""
EYEQ – Intelligent Vision Security System
Configuration & Settings Module

Centralizes all environment variables and application settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Application ───────────────────────────────────────────────
APP_NAME = "EYEQ"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-use-strong-random-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# ─── Database ──────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./eyeq.db")

# ─── Twilio SMS ────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
ADMIN_PHONE_NUMBER = os.getenv("ADMIN_PHONE_NUMBER", "")

# ─── Email / SMTP ──────────────────────────────────────────────
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", EMAIL_ADDRESS)

# ─── Detection ─────────────────────────────────────────────────
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "detection/models/yolov8n.pt")
DETECTION_CONFIDENCE = float(os.getenv("DETECTION_CONFIDENCE", 0.25))
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", 30))

# ── All monitored object labels ────────────────────────────────
# Covers all 80 COCO classes + custom threat objects.
# Every detected object below will trigger an alert.
# Comment out any label you do NOT want to alert on.

SUSPICIOUS_LABELS = {

    # ── People ─────────────────────────────────────────────────
    "person",

    # ── Vehicles ───────────────────────────────────────────────
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",

    # ── Traffic / Street Objects ───────────────────────────────
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",

    # ── Animals ────────────────────────────────────────────────
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",

    # ── Carry / Luggage ────────────────────────────────────────
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",

    # ── Sports Equipment ───────────────────────────────────────
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",

    # ── Kitchen / Food Items ───────────────────────────────────
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",          # weapon / threat
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",

    # ── Furniture ──────────────────────────────────────────────
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",

    # ── Electronics / Valuables ────────────────────────────────
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",

    # ── Miscellaneous Objects ──────────────────────────────────
    "book",
    "clock",
    "vase",
    "scissors",       # weapon / threat
    "teddy bear",
    "hair drier",
    "toothbrush",

    # ── Custom Threat Labels (non-COCO, needs custom model) ────
    "gun",
    "pistol",
    "rifle",
    "shotgun",
    "weapon",
    "mask",           # face covering / suspicious
    "helmet",
    "crowbar",
    "bat",
    "explosive",
    "fire",
    "smoke",
}

# ─── Paths ─────────────────────────────────────────────────────
ALERT_IMAGES_DIR = os.getenv("ALERT_IMAGES_DIR", "alert_images")
LOG_DIR = os.getenv("LOG_DIR", "logs")

# ─── Rate Limiting ─────────────────────────────────────────────
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", 60))

# ─── Camera ────────────────────────────────────────────────────
DEFAULT_WEBCAM_INDEX = int(os.getenv("DEFAULT_WEBCAM_INDEX", 0))
FRAME_SKIP = int(os.getenv("FRAME_SKIP", 1))   # process every frame (set higher for performance)
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", 80))
