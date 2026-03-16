"""
EYEQ – AI Detection Engine

Pipeline:
  Camera Feed → Frame Extraction → YOLOv8 Inference → Event Trigger → Alert

Key responsibilities:
  - Load and cache the YOLOv8 model
  - Run inference on individual frames
  - Draw annotated bounding boxes
  - Determine whether a detection is "suspicious"
  - Enforce an alert cooldown to avoid spam
"""

import time
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Callable

import cv2
import numpy as np

# ultralytics is imported lazily so the module can be loaded without GPU
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

from config.settings import (
    YOLO_MODEL_PATH,
    DETECTION_CONFIDENCE,
    ALERT_COOLDOWN_SECONDS,
    SUSPICIOUS_LABELS,
    FRAME_SKIP,
)
from utils.helpers import get_logger, save_alert_frame

logger = get_logger(__name__)


# ─── Data Classes ──────────────────────────────────────────────

@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple          # (x1, y1, x2, y2)
    is_suspicious: bool = False


@dataclass
class FrameResult:
    frame: np.ndarray                   # annotated frame
    detections: List[Detection] = field(default_factory=list)
    has_alert: bool = False
    alert_image_path: Optional[str] = None


# ─── Detector ──────────────────────────────────────────────────

class EYEQDetector:
    """
    Wraps a YOLOv8 model and provides frame-level detection with:
      - suspicious-object filtering
      - cooldown-aware alerting
      - annotated frame output
    """

    _FONT = cv2.FONT_HERSHEY_SIMPLEX

    # Color map per category (BGR)
    _CATEGORY_COLORS = {
        # Weapons / high threat → RED
        "knife": (0, 0, 255), "gun": (0, 0, 255), "pistol": (0, 0, 255),
        "rifle": (0, 0, 255), "shotgun": (0, 0, 255), "weapon": (0, 0, 255),
        "scissors": (0, 0, 220), "crowbar": (0, 0, 220), "bat": (0, 0, 220),
        "explosive": (0, 0, 200), "fire": (0, 60, 255), "smoke": (80, 80, 255),

        # People → ORANGE
        "person": (0, 140, 255),

        # Vehicles → CYAN
        "car": (255, 200, 0), "truck": (255, 180, 0), "bus": (255, 160, 0),
        "motorcycle": (255, 220, 0), "bicycle": (200, 220, 0),
        "airplane": (220, 255, 0), "train": (180, 255, 0), "boat": (160, 255, 0),

        # Electronics / valuables → PURPLE
        "laptop": (200, 0, 200), "cell phone": (180, 0, 200),
        "tv": (160, 0, 180), "keyboard": (140, 0, 160),

        # Luggage / carry → YELLOW
        "backpack": (0, 220, 220), "suitcase": (0, 200, 200),
        "handbag": (0, 180, 180), "umbrella": (0, 160, 160),

        # Animals → TEAL
        "dog": (150, 200, 50), "cat": (130, 200, 50), "bird": (110, 200, 50),
        "horse": (90, 180, 50), "cow": (70, 180, 50), "bear": (50, 160, 50),
        "elephant": (50, 140, 50), "sheep": (50, 120, 50),

        # Suspicious accessories → PINK
        "mask": (180, 100, 255), "helmet": (160, 80, 255),
    }
    _COLOR_DEFAULT = (0, 200, 0)   # green for unlisted labels

    def __init__(self, on_alert: Optional[Callable[[Detection, str], None]] = None):
        """
        Args:
            on_alert: Optional callback invoked when a suspicious detection
                      passes the cooldown gate.
                      Signature: on_alert(detection, image_path)
        """
        self._model = None
        self._last_alert_time: dict = {}   # label -> last alert timestamp
        self._lock = threading.Lock()
        self._on_alert = on_alert
        self._frame_counter = 0
        self._load_model()

    # ── Model Loading ─────────────────────────────────────────

    def _load_model(self):
        if not YOLO_AVAILABLE:
            logger.warning("ultralytics not installed. Running in DEMO mode (no real inference).")
            return
        try:
            self._model = YOLO(YOLO_MODEL_PATH)
            logger.info("YOLOv8 model loaded from: %s", YOLO_MODEL_PATH)
        except Exception as exc:
            logger.error("Failed to load YOLO model: %s", exc)
            self._model = None

    # ── Core Inference ────────────────────────────────────────

    def process_frame(self, frame: np.ndarray, camera_source: str = "") -> FrameResult:
        """
        Run detection on a single BGR frame.

        Args:
            frame: OpenCV BGR image.
            camera_source: Identifier string for alert logging.

        Returns:
            FrameResult with annotated frame and detection metadata.
        """
        self._frame_counter += 1

        # Skip frames for performance
        if self._frame_counter % FRAME_SKIP != 0:
            return FrameResult(frame=frame)

        annotated = frame.copy()
        detections: List[Detection] = []
        has_alert = False
        alert_image_path = None

        if self._model is None:
            # Demo mode – return un-annotated frame
            return FrameResult(frame=annotated, detections=detections)

        try:
            results = self._model(frame, conf=DETECTION_CONFIDENCE, verbose=False)
        except Exception as exc:
            logger.error("Inference error: %s", exc)
            return FrameResult(frame=annotated)

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = result.names.get(cls_id, "unknown")
                suspicious = label.lower() in SUSPICIOUS_LABELS

                det = Detection(
                    label=label,
                    confidence=conf,
                    bbox=(x1, y1, x2, y2),
                    is_suspicious=suspicious,
                )
                detections.append(det)
                self._draw_box(annotated, det)

                if suspicious and self._cooldown_passed(label):
                    has_alert = True
                    alert_image_path = save_alert_frame(annotated, label)
                    self._update_cooldown(label)
                    if self._on_alert:
                        try:
                            self._on_alert(det, alert_image_path)
                        except Exception as cb_exc:
                            logger.error("Alert callback error: %s", cb_exc)

        return FrameResult(
            frame=annotated,
            detections=detections,
            has_alert=has_alert,
            alert_image_path=alert_image_path,
        )

    # ── Annotation ────────────────────────────────────────────

    def _draw_box(self, frame: np.ndarray, det: Detection):
        """Draw a bounding box and label on the frame in-place."""
        x1, y1, x2, y2 = det.bbox
        color = self._CATEGORY_COLORS.get(det.label.lower(), self._COLOR_DEFAULT)
        label_text = f"{det.label} {det.confidence:.0%}"

        # Rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Label background
        (tw, th), _ = cv2.getTextSize(label_text, self._FONT, 0.55, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)

        # Label text
        cv2.putText(frame, label_text, (x1 + 2, y1 - 4), self._FONT, 0.55, (255, 255, 255), 1)

        # "ALERT" banner for suspicious detections
        if det.is_suspicious:
            cv2.putText(frame, "⚠ SUSPICIOUS", (x1, y2 + 18), self._FONT, 0.6, self._COLOR_ALERT, 2)

    # ── Cooldown ──────────────────────────────────────────────

    def _cooldown_passed(self, label: str) -> bool:
        with self._lock:
            last = self._last_alert_time.get(label, 0)
            return (time.time() - last) >= ALERT_COOLDOWN_SECONDS

    def _update_cooldown(self, label: str):
        with self._lock:
            self._last_alert_time[label] = time.time()


# ─── Camera Stream Loop ────────────────────────────────────────

class CameraStream:
    """
    Opens a camera source, runs the detector on each frame,
    and makes the latest annotated frame available via `get_frame()`.

    Usage (threaded):
        stream = CameraStream(source=0, detector=detector)
        stream.start()
        ...
        frame = stream.get_frame()
        ...
        stream.stop()
    """

    def __init__(self, source, detector: EYEQDetector):
        # source can be int (webcam), str (RTSP URL or file path)
        self._source = int(source) if str(source).isdigit() else source
        self._detector = detector
        self._cap: Optional[cv2.VideoCapture] = None
        self._latest_result: Optional[FrameResult] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._cap = cv2.VideoCapture(self._source)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera source: {self._source}")
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("CameraStream started: source=%s", self._source)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._cap:
            self._cap.release()
        logger.info("CameraStream stopped: source=%s", self._source)

    def get_frame(self) -> Optional[FrameResult]:
        with self._lock:
            return self._latest_result

    def _loop(self):
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("CameraStream: failed to read frame from %s", self._source)
                time.sleep(0.1)
                continue
            result = self._detector.process_frame(frame, camera_source=str(self._source))
            with self._lock:
                self._latest_result = result
