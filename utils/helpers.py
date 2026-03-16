"""
EYEQ – Utility Helpers

General-purpose utilities used across the project:
  - directory bootstrapping
  - logging setup
  - timestamp helpers
  - image I/O
  - token generation
"""

import os
import uuid
import logging
import base64
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from config.settings import ALERT_IMAGES_DIR, LOG_DIR, JPEG_QUALITY


# ─── Logging ───────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(Path(LOG_DIR) / "eyeq.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ─── Directory Setup ───────────────────────────────────────────

def bootstrap_directories():
    """Create required runtime directories if they don't exist."""
    dirs = [ALERT_IMAGES_DIR, LOG_DIR, "detection/models"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


# ─── Timestamps ────────────────────────────────────────────────

def utc_now_str() -> str:
    """Return the current UTC datetime as a human-readable string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def filename_timestamp() -> str:
    """Return a filesystem-safe timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


# ─── Image Utilities ───────────────────────────────────────────

def save_alert_frame(frame: np.ndarray, label: str) -> str:
    """
    Save a detection frame to the alert images directory.

    Args:
        frame: BGR OpenCV image array.
        label: Detection label used in the filename.

    Returns:
        Absolute path of the saved image.
    """
    Path(ALERT_IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    safe_label = label.replace(" ", "_")
    filename = f"{filename_timestamp()}_{safe_label}.jpg"
    filepath = str(Path(ALERT_IMAGES_DIR) / filename)
    cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return filepath


def frame_to_base64(frame: np.ndarray) -> str:
    """Encode an OpenCV frame as a base64 JPEG string (for API/Streamlit)."""
    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return base64.b64encode(buffer).decode("utf-8")


def base64_to_frame(b64_str: str) -> np.ndarray:
    """Decode a base64 JPEG string back to an OpenCV frame."""
    img_bytes = base64.b64decode(b64_str)
    np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


# ─── Misc ──────────────────────────────────────────────────────

def generate_unique_id() -> str:
    """Return a short unique identifier."""
    return str(uuid.uuid4())
