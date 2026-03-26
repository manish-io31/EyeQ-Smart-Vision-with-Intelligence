"""
Flask + AWS Rekognition Surveillance System
Configuration Module
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Flask ─────────────────────────────────────────────────────
SECRET_KEY      = os.getenv("SECRET_KEY", "eyeq-surveillance-secret-2024")
DEBUG           = os.getenv("DEBUG", "false").lower() == "true"
SESSION_PERMANENT           = True
PERMANENT_SESSION_LIFETIME  = int(os.getenv("SESSION_LIFETIME_HOURS", 24)) * 3600

# ─── Database ──────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./surveillance.db")

# ─── AWS Rekognition ───────────────────────────────────────────
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION            = os.getenv("AWS_REGION", "us-east-1")
# S3 bucket for video moderation (optional — frame-extraction used if empty)
AWS_S3_BUCKET         = os.getenv("AWS_S3_BUCKET", "")

# ─── Detection ─────────────────────────────────────────────────
# Lower detection threshold catches small objects (phones, knives) with fewer false negatives.
# Alert threshold stays higher to avoid noisy SMS alerts.
DETECTION_CONFIDENCE_THRESHOLD = float(os.getenv("DETECTION_CONFIDENCE_THRESHOLD", 35.0))
ALERT_CONFIDENCE_THRESHOLD     = float(os.getenv("ALERT_CONFIDENCE_THRESHOLD", 65.0))
ALERT_COOLDOWN_SECONDS         = int(os.getenv("ALERT_COOLDOWN_SECONDS", 30))

# Labels that always trigger SMS/email alert
HIGH_THREAT_LABELS = {
    "person", "weapon", "gun", "knife", "pistol", "rifle",
    "scissors", "fire", "smoke", "mask", "cell phone", "laptop",
    "backpack", "car", "motorcycle", "truck",
}

# ─── Twilio SMS ────────────────────────────────────────────────
TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER  = os.getenv("TWILIO_FROM_NUMBER", "")

# ★ DEFAULT PHONE — alerts always go here
ADMIN_PHONE_NUMBER  = os.getenv("ADMIN_PHONE_NUMBER", "+91XXXXXXXXXX")

# ─── Email / SMTP ──────────────────────────────────────────────
EMAIL_ADDRESS  = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_HOST      = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT      = int(os.getenv("SMTP_PORT", 587))
ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL", EMAIL_ADDRESS)

# ─── YOLO fallback ─────────────────────────────────────────────
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "../detection/models/yolov8n.pt")
