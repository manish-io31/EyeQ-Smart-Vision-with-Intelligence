"""Database models — Flask-SQLAlchemy ORM"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(16),  default="admin")
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def is_admin(self):
        return self.role == "admin"


class AlertEvent(db.Model):
    __tablename__ = "alert_events"
    id               = db.Column(db.Integer, primary_key=True)
    object_detected  = db.Column(db.String(128), nullable=False)
    confidence_score = db.Column(db.Float,   nullable=False)
    detection_type   = db.Column(db.String(32),  default="yolo")
    camera_source    = db.Column(db.String(256), default="webcam")
    image_path       = db.Column(db.String(512), nullable=True)
    alert_sent       = db.Column(db.Boolean,     default=False)
    sms_sent         = db.Column(db.Boolean,     default=False)
    timestamp        = db.Column(db.DateTime,    default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id":               self.id,
            "object_detected":  self.object_detected,
            "confidence_score": round(self.confidence_score, 2),
            "detection_type":   self.detection_type,
            "camera_source":    self.camera_source,
            "image_path":       self.image_path,
            "alert_sent":       self.alert_sent,
            "sms_sent":         self.sms_sent,
            "timestamp":        self.timestamp.isoformat() + "Z",
        }


class DetectionLog(db.Model):
    __tablename__ = "detection_log"
    id             = db.Column(db.Integer, primary_key=True)
    label          = db.Column(db.String(128), nullable=False, index=True)
    confidence     = db.Column(db.Float,   nullable=False)
    detection_type = db.Column(db.String(32),  default="yolo")
    bounding_box   = db.Column(db.String(256), nullable=True)
    camera_source  = db.Column(db.String(256), default="webcam")
    timestamp      = db.Column(db.DateTime,    default=datetime.utcnow, index=True)

    def to_dict(self):
        import json
        return {
            "id":             self.id,
            "label":          self.label,
            "confidence":     round(self.confidence, 2),
            "detection_type": self.detection_type,
            "bounding_box":   json.loads(self.bounding_box) if self.bounding_box else None,
            "camera_source":  self.camera_source,
            "timestamp":      self.timestamp.isoformat() + "Z",
        }
