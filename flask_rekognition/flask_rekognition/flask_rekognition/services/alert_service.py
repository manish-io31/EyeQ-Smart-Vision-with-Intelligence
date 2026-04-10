"""
Alert Service — SMS (Twilio) + Email (SMTP) + per-label cooldown
"""

import smtplib
import logging
import time
import threading
import json
import mimetypes
import os
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import config

logger = logging.getLogger(__name__)
_TG_TIMEOUT = 12

try:
    from twilio.rest import Client as TwilioClient
    _TWILIO = True
except ImportError:
    _TWILIO = False

# Per-label cooldown
_lock = threading.Lock()
_last: dict = {}


def _cooldown_ok(label: str) -> bool:
    with _lock:
        return (time.time() - _last.get(label, 0)) >= config.ALERT_COOLDOWN_SECONDS


def _update(label: str):
    with _lock:
        _last[label] = time.time()


# ─── SMS ───────────────────────────────────────────────────────

def send_sms(label: str, confidence: float, camera: str = "webcam",
             use_cooldown: bool = True) -> bool:
    """
    Send SMS to ADMIN_PHONE_NUMBER via Twilio.

    HOW TO RECEIVE THE SMS ON YOUR MOBILE:
      1. Sign up at https://twilio.com (free trial)
      2. Get:  Account SID, Auth Token, Twilio phone number
      3. Set in .env:
            TWILIO_ACCOUNT_SID=ACxxxxxxxx
            TWILIO_AUTH_TOKEN=your_token
            TWILIO_FROM_NUMBER=+1XXXXXXXXXX  ← Twilio number
            ADMIN_PHONE_NUMBER=+91XXXXXXXXXX ← YOUR mobile
      4. Alerts fire automatically when a threat is detected
    """
    if not _TWILIO:
        logger.warning("twilio not installed. pip install twilio")
        return False
    if not all([config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN,
                config.TWILIO_FROM_NUMBER, config.ADMIN_PHONE_NUMBER]):
        logger.warning("Twilio credentials missing in .env")
        return False
    if use_cooldown and not _cooldown_ok(label):
        return False

    ts   = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    body = (
        f"ALERT: {label} detected!\n"
        f"Confidence: {confidence:.0f}%\n"
        f"Camera: {camera}\n"
        f"Time: {ts}\n"
        f"Check dashboard: http://localhost:5000"
    )

    try:
        client = TwilioClient(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body  = body,
            from_ = config.TWILIO_FROM_NUMBER,
            to    = config.ADMIN_PHONE_NUMBER,
        )
        if use_cooldown:
            _update(label)
        logger.info("SMS sent  SID=%s  to=%s  label=%s",
                    msg.sid, config.ADMIN_PHONE_NUMBER, label)
        return True
    except Exception as e:
        logger.error("SMS failed: %s", e)
        return False


# ─── Telegram ───────────────────────────────────────────────────

def _telegram_api(method: str, payload: dict, image_path: Optional[str] = None) -> dict:
    token = config.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/{method}"

    if image_path:
        boundary = f"----EyeQBoundary{uuid.uuid4().hex}"
        mime_type = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
        filename = os.path.basename(image_path) or "alert.jpg"
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        body = bytearray()
        for key, value in payload.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
            body.extend(str(value).encode())
            body.extend(b"\r\n")

        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode()
        )
        body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode())
        body.extend(image_bytes)
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())

        req = Request(
            url,
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
    else:
        data = urlencode(payload).encode()
        req = Request(url, data=data, method="POST")

    with urlopen(req, timeout=_TG_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_telegram(label: str, confidence: float, camera: str = "webcam",
                  image_path: Optional[str] = None, use_cooldown: bool = True) -> bool:
    if not all([config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID]):
        logger.warning("Telegram credentials missing in .env")
        return False
    if use_cooldown and not _cooldown_ok(label):
        return False

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    text = (
        "⚠️ EYEQ ALERT\n"
        f"Object: {label}\n"
        f"Confidence: {confidence:.0f}%\n"
        f"Camera: {camera}\n"
        f"Time: {ts}\n"
        "Dashboard: http://localhost:5000"
    )
    payload = {"chat_id": config.TELEGRAM_CHAT_ID, "caption": text, "text": text}

    try:
        sent = False
        if image_path and os.path.exists(image_path):
            res = _telegram_api("sendPhoto", payload, image_path=image_path)
            sent = bool(res.get("ok"))
            if not sent:
                logger.warning("Telegram sendPhoto failed, fallback to sendMessage")

        if not sent:
            res = _telegram_api("sendMessage", payload, image_path=None)
            sent = bool(res.get("ok"))

        if sent:
            if use_cooldown:
                _update(label)
            logger.info("Telegram sent  chat_id=%s  label=%s", config.TELEGRAM_CHAT_ID, label)
            return True

        logger.error("Telegram failed: %s", res)
        return False
    except Exception as e:
        logger.error("Telegram failed: %s", e)
        return False


# ─── Email ─────────────────────────────────────────────────────

def send_email(label: str, confidence: float, camera: str = "webcam",
               image_path: Optional[str] = None) -> bool:
    if not all([config.EMAIL_ADDRESS, config.EMAIL_PASSWORD, config.ADMIN_EMAIL]):
        return False

    ts      = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"SURVEILLANCE ALERT: {label} detected"
    html    = f"""
    <html><body style="font-family:Arial;background:#0f172a;color:#e2e8f0;padding:20px;">
    <div style="max-width:560px;margin:auto;background:#1e293b;border-radius:12px;
                padding:24px;border:2px solid #ef4444;">
      <h2 style="color:#ef4444;">&#9888; Surveillance Alert</h2>
      <table>
        <tr><td style="color:#94a3b8;padding:6px 16px 6px 0">Object</td>
            <td style="font-weight:bold">{label}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 16px 6px 0">Confidence</td>
            <td>{confidence:.1f}%</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 16px 6px 0">Camera</td>
            <td>{camera}</td></tr>
        <tr><td style="color:#94a3b8;padding:6px 16px 6px 0">Time</td>
            <td>{ts}</td></tr>
      </table>
      <p style="color:#64748b;margin-top:16px;">Check your surveillance dashboard immediately.</p>
    </div></body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = config.EMAIL_ADDRESS
    msg["To"]      = config.ADMIN_EMAIL
    msg.attach(MIMEText(html, "html"))

    if image_path:
        try:
            with open(image_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment; filename=alert.jpg")
            msg.attach(part)
        except Exception as e:
            logger.warning("Image attach failed: %s", e)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
            s.ehlo(); s.starttls()
            s.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
            s.sendmail(config.EMAIL_ADDRESS, config.ADMIN_EMAIL, msg.as_string())
        return True
    except Exception as e:
        logger.error("Email failed: %s", e)
        return False


# ─── Dispatcher ────────────────────────────────────────────────

def dispatch_alert(label: str, confidence: float, camera: str = "webcam",
                   image_path: Optional[str] = None):
    """Fire SMS + email in a background thread (non-blocking)."""
    def _fire():
        sms_ok   = send_sms(label, confidence, camera, use_cooldown=False)
        tg_ok    = send_telegram(label, confidence, camera, image_path, use_cooldown=False)
        email_ok = send_email(label, confidence, camera, image_path)
        logger.info(
            "Alert dispatched  sms=%s  telegram=%s  email=%s  label=%s",
            sms_ok, tg_ok, email_ok, label
        )

    threading.Thread(target=_fire, daemon=True).start()
