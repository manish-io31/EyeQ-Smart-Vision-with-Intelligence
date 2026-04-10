# EyeQ — Smart Vision Surveillance System

## Complete Project Documentation


## Table of Contents

1. [Project Summary](#1-project-summary)  
2. [Objectives](#2-objectives)  
3. [Technology Stack](#3-technology-stack)  
4. [System Architecture](#4-system-architecture)  
5. [Current Project Structure](#5-current-project-structure)  
6. [Core Modules](#6-core-modules)  
7. [Detection Engine (AWS / YOLO / Demo)](#7-detection-engine-aws--yolo--demo)  
8. [Alert Engine (SMS / Telegram / Email)](#8-alert-engine-sms--telegram--email)  
9. [Authentication, Sessions, and Roles](#9-authentication-sessions-and-roles)  
10. [Database Schema](#10-database-schema)  
11. [Frontend and Real-Time UI Flow](#11-frontend-and-real-time-ui-flow)  
12. [API Reference](#12-api-reference)  
13. [Environment Variables](#13-environment-variables)  
14. [Installation and Run Guide](#14-installation-and-run-guide)  
15. [How to Test the Project](#15-how-to-test-the-project)  
16. [Performance Notes and Tuning](#16-performance-notes-and-tuning)  
17. [Known Limitations](#17-known-limitations)  
18. [Troubleshooting Guide](#18-troubleshooting-guide)  
19. [Security Guidance](#19-security-guidance)  
20. [Future Enhancements](#20-future-enhancements)

---

## 1. Project Summary

EyeQ is a Flask-based intelligent surveillance platform that:

- accepts live camera input from webcam, RTSP streams, and local video,
- performs object detection in near real-time,
- stores detections and alert history,
- dispatches notifications through SMS, Telegram, and Email,
- provides dashboard analytics and alert history through a web UI.

The project follows a practical fallback strategy:

1. Use AWS Rekognition when configured.  
2. Otherwise use YOLO locally.  
3. Otherwise run demo mode so UI still functions.

---

## 2. Objectives

- Build an end-to-end surveillance application, not just a detector script.
- Provide immediate threat notification to operators.
- Maintain detection history for auditing and analytics.
- Support multiple camera sources with one unified interface.
- Keep project usable in low-resource environments through fallback modes.

---

## 3. Technology Stack

### Backend

- Python
- Flask
- Flask-Login
- Flask-SQLAlchemy
- python-dotenv

### Detection and Vision

- AWS Rekognition (`boto3`)
- YOLO (Ultralytics)
- OpenCV
- NumPy
- Pillow
- Optional OCR via `pytesseract`

### Notifications

- Twilio SMS
- Telegram Bot API (direct HTTP requests)
- SMTP Email (`smtplib`)

### Frontend

- Jinja templates
- Bootstrap 5
- Vanilla JavaScript
- Chart.js

### Database

- SQLite by default (`instance/surveillance.db`)
- PostgreSQL possible through `DATABASE_URL`

---

## 4. System Architecture

```text
Camera Source (Webcam / RTSP / Local Video)
            ↓
Frame Capture + Compression (camera.js)
            ↓
POST /api/detect (Flask)
            ↓
Detection Service (Rekognition -> YOLO -> Demo)
            ↓
Threat Decision + Cooldown
            ↓
Store Event + Notification Dispatch
            ↓
Dashboard + Alerts History + Charts
```

---

## 5. Current Project Structure

```text
EyeQ-Smart-Vision-with-Intelligence/
├── DOCUMENTATION.md
├── config/
│   └── settings.py
└── flask_rekognition/
    ├── app.py
    ├── config.py
    ├── models.py
    ├── requirements.txt
    ├── .env
    ├── routes/
    │   ├── auth.py
    │   ├── dashboard.py
    │   ├── camera.py
    │   ├── alerts.py
    │   ├── detection.py
    │   └── moderation.py
    ├── services/
    │   ├── rekognition_service.py
    │   └── alert_service.py
    ├── templates/
    │   ├── base.html
    │   ├── login.html
    │   ├── dashboard.html
    │   ├── alerts.html
    │   ├── image_detection.html
    │   └── moderation.html
    ├── static/
    │   ├── css/style.css
    │   ├── js/camera.js
    │   ├── js/dashboard.js
    │   └── img/eyeq-logo.png
    ├── instance/
    │   └── surveillance.db
    └── snapshots/   (runtime generated)
```

---

## 6. Core Modules

### 6.1 `app.py`

- Creates Flask app.
- Loads config from `config.py`.
- Initializes DB and LoginManager.
- Registers all blueprints.
- Creates default admin if no user exists.
- Provides `/favicon.ico`.

### 6.2 `routes/auth.py`

- `/auth/login` (GET/POST)
- `/auth/register` (GET/POST)
- `/auth/logout`
- `/auth/me` (session health endpoint)

### 6.3 `routes/camera.py`

- `/api/detect` — real-time detection endpoint for live feed.
- `/api/status` — backend mode/status for UI.
- `/api/snapshot` — manual image save.
- `/api/rtsp/feed` — MJPEG stream proxy.

### 6.4 `routes/dashboard.py`

- `/dashboard` page
- `/api/stats` for summary cards, charts, recent alerts

### 6.5 `routes/alerts.py`

- `/alerts` page
- `/api/alerts` listing with filters and pagination
- `/api/alerts/<id>` details
- `/api/alerts/summary` count for navbar badge
- `/api/alerts/test-telegram` for test dispatch (admin protected)

### 6.6 `routes/detection.py`

- `/image-detection` page
- `/detect-image` uploaded image analysis

### 6.7 `routes/moderation.py`

- Age verification flow
- Image moderation using Rekognition moderation labels
- Video moderation via frame sampling or optional S3-based flow

### 6.8 `services/rekognition_service.py`

- Unified detector with fallback.
- Normalizes output format.
- Threat label normalization and matching logic.

### 6.9 `services/alert_service.py`

- Per-label cooldown.
- Sends SMS, Telegram, Email.
- Returns channel delivery result map for downstream persistence/UI.

---

## 7. Detection Engine (AWS / YOLO / Demo)

### Priority order

1. Rekognition backend (if AWS credentials valid)  
2. YOLO backend (if model installed)  
3. Demo backend

### Output contract

Every backend returns list entries like:

```json
{
  "label": "person",
  "confidence": 87.5,
  "detection_type": "label|yolo|face|text|moderation|demo",
  "bounding_box": {"Left":0.1,"Top":0.2,"Width":0.3,"Height":0.4},
  "color": "#hex",
  "is_alert": true
}
```

### Threat matching

- Label text is normalized (case/separator/punctuation).
- Matching supports exact and partial compound matches.
- `ALERT_CONFIDENCE_THRESHOLD` is required for alert trigger.

---

## 8. Alert Engine (SMS / Telegram / Email)

### Channel behavior

- SMS via Twilio (`send_sms`)
- Telegram via Bot API (`send_telegram`)
- Email via SMTP (`send_email`)

### Dispatch behavior

`dispatch_alert(...)` returns:

```python
{"sms": bool, "telegram": bool, "email": bool}
```

In camera flow, Telegram status is currently persisted into `AlertEvent.sms_sent` to drive the table tick/cross icon.

### Cooldown

- Per-label cooldown is enforced with in-memory time map.
- Prevents notification spam for repeated detections.

---

## 9. Authentication, Sessions, and Roles

### User model

- `username`
- `email`
- `password_hash`
- `role` (default currently set in model as `"admin"`, registration route assigns `"user"`)

### Session

- Permanent session enabled.
- Remember cookie configured.
- Session health checked from frontend via `/auth/me`.

### Default account

Created automatically on first startup if DB has no users:

- Username: `admin`
- Password: `Admin@1234`

---

## 10. Database Schema

### `users`

- `id` (PK)
- `username` (unique)
- `email` (unique nullable)
- `password_hash`
- `role`
- `created_at`

### `alert_events`

- `id` (PK)
- `object_detected`
- `confidence_score`
- `detection_type`
- `camera_source`
- `image_path`
- `alert_sent`
- `sms_sent` (used as notification status flag in UI)
- `timestamp`

### `detection_log`

- `id` (PK)
- `label`
- `confidence`
- `detection_type`
- `bounding_box` (JSON string)
- `camera_source`
- `timestamp`

---

## 11. Frontend and Real-Time UI Flow

### Live detection frontend (`static/js/camera.js`)

- Render loop: `requestAnimationFrame` for smooth box drawing.
- Detection loop: periodic POST to `/api/detect`.
- Busy-flag to avoid overlapping requests.
- Offscreen canvas compression before upload.

Current fast settings:

- `DETECT_INTERVAL = 250 ms`
- `MAX_W = 480`
- `QUALITY = 0.60`

### Dashboard frontend (`static/js/dashboard.js`)

- Polls `/api/stats` periodically.
- Updates summary cards and Chart.js in-place.
- Updates recent alerts table and notification badge.

---

## 12. API Reference

### Auth

- `GET/POST /auth/login`
- `GET/POST /auth/register`
- `GET /auth/logout`
- `GET /auth/me`

### Dashboard

- `GET /dashboard`
- `GET /api/stats`

### Live camera

- `POST /api/detect`
- `GET /api/status`
- `POST /api/snapshot`
- `GET /api/rtsp/feed?url=...`

### Alerts

- `GET /alerts`
- `GET /api/alerts?page=1&per_page=25&label=...&min_confidence=...`
- `GET /api/alerts/<id>`
- `DELETE /api/alerts/<id>` (admin)
- `GET /api/alerts/summary`
- `GET/POST /api/alerts/test-telegram` (admin)

### Image detection

- `GET /image-detection`
- `POST /detect-image`

### Moderation

- `GET /moderation`
- `POST /verify-age`
- `POST /moderate-image`
- `POST /moderate-video`

---

## 13. Environment Variables

Create `flask_rekognition/.env`:

```env
# Core
SECRET_KEY=change-this
DEBUG=false
DATABASE_URL=sqlite:///./surveillance.db

# Detection tuning
DETECTION_CONFIDENCE_THRESHOLD=35
ALERT_CONFIDENCE_THRESHOLD=65
ALERT_COOLDOWN_SECONDS=30
LOG_ALL_DETECTIONS=false

# AWS (optional)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
AWS_S3_BUCKET=

# Twilio (optional)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
ADMIN_PHONE_NUMBER=

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Email (optional)
EMAIL_ADDRESS=
EMAIL_PASSWORD=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
ADMIN_EMAIL=

# YOLO model
YOLO_MODEL_PATH=../detection/models/yolov8n.pt
```

> Never commit real tokens/passwords.

---

## 14. Installation and Run Guide

```bash
cd "d:\manish\MAJOR PROJECT\EyeQ-Smart-Vision-with-Intelligence\flask_rekognition"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open:

- `http://127.0.0.1:5000`

---

## 15. How to Test the Project

### Basic functional test

1. Login with admin.
2. Start webcam in dashboard.
3. Observe live boxes + stats update.
4. Open alerts page and verify latest records.

### Telegram test

1. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
2. Restart app.
3. Visit `/api/alerts/test-telegram` (admin logged in).
4. Verify Telegram message delivery.

### Role test

1. Register new user.
2. Login as that user.
3. Verify available pages and data according to current role policy.

---

## 16. Performance Notes and Tuning

### Current optimizations

- Reduced live frame upload size/quality.
- Adjustable detection interval.
- Optional DB write reduction via `LOG_ALL_DETECTIONS=false`.
- Threaded RTSP frame capture queue with frame dropping to limit lag.

### If still slow

- Lower detection width further.
- Increase detection interval (e.g., 300–400 ms).
- Disable OCR if not needed.
- Use GPU-backed inference where possible.

---

## 17. Known Limitations

- 100% detection accuracy is not technically guaranteed.
- Model capability depends on available classes in chosen backend.
- OCR requires Tesseract system binary for full text mode.
- Local server setup is not production hardened by default.

---

## 18. Troubleshooting Guide

### Telegram not sending

- Ensure both token and chat id exist in `.env`.
- Start bot conversation first.
- Verify with `getUpdates`.
- Restart app after `.env` edits.

### Twilio not sending

- Verify SID/token/from/to numbers.
- Trial accounts require destination number verification.

### No detections

- Check `/api/status` mode.
- Confirm camera access permissions.
- Lower confidence thresholds.

### Slow UI

- Use lower camera resolution.
- Increase detect interval.
- Keep DB logging minimal.

---

## 19. Security Guidance

- Rotate any token once exposed.
- Keep `.env` out of source control.
- Use HTTPS and secure cookies in production.
- Replace default admin credentials immediately.
- Add rate limiting and CSRF hardening for production deployment.

---

## 20. Future Enhancements

- Fine-tuned custom detector for your full label set.
- True role-based data scoping and permissions matrix.
- Queue-based async notifications (Celery/RQ).
- WebSocket updates instead of polling.
- Dockerized deployment profile.
- Multi-tenant camera/device management.

---

## Document Metadata

- Last updated: 2026-04-10 15:48:16
- Project: EyeQ Smart Vision with Intelligence
- Main app path: `flask_rekognition/`
 * Running on http://0.0.0.0:5000
 * Debug mode: off
```

### Step 7 — Open in Browser

Go to: **http://127.0.0.1:5000**

You will be redirected to the login page automatically.

### Default Login Credentials

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `Admin@1234` |

> These credentials are only created if no users exist in the database (first run).

---

## 5. Configuration & Environment Variables

All configuration lives in `config.py`. Values are read from the `.env` file using `python-dotenv`.

### Flask Settings

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `eyeq-surveillance-secret-2024` | Flask session encryption key — change in production |
| `DEBUG` | `false` | Enable Flask debug mode |
| `SESSION_LIFETIME_HOURS` | `24` | How long login session lasts |

### Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./surveillance.db` | Database connection string |

For PostgreSQL: `DATABASE_URL=postgresql://user:password@localhost/eyeq`

### AWS Rekognition

| Variable | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key |
| `AWS_REGION` | AWS region (e.g., `us-east-1`) |
| `AWS_S3_BUCKET` | Optional S3 bucket for video moderation |

> If these are empty, the app falls back to YOLOv8 automatically.

### Detection Thresholds

| Variable | Default | Description |
|---|---|---|
| `DETECTION_CONFIDENCE_THRESHOLD` | `35.0` | Minimum confidence % to show a detection |
| `ALERT_CONFIDENCE_THRESHOLD` | `65.0` | Minimum confidence % to trigger an alert |
| `ALERT_COOLDOWN_SECONDS` | `30` | Seconds to wait before re-alerting for the same label |

### Threat Labels (Hardcoded in config.py)

These labels will trigger SMS/email alerts when detected above threshold:

```
person, weapon, gun, knife, pistol, rifle,
scissors, fire, smoke, mask, cell phone, laptop,
backpack, car, motorcycle, truck
```

### Twilio SMS

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Your Twilio account SID (starts with AC) |
| `TWILIO_AUTH_TOKEN` | Your Twilio auth token |
| `TWILIO_FROM_NUMBER` | The Twilio phone number that sends the SMS |
| `ADMIN_PHONE_NUMBER` | Your personal phone number that receives alerts |

### SMTP Email

| Variable | Default | Description |
|---|---|---|
| `EMAIL_ADDRESS` | — | Gmail address that sends alerts |
| `EMAIL_PASSWORD` | — | Gmail App Password (not your regular password) |
| `ADMIN_EMAIL` | Same as `EMAIL_ADDRESS` | Address that receives alert emails |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port (TLS) |

> For Gmail: Go to Google Account → Security → App Passwords → Generate one for "Mail".

### YOLO Settings

| Variable | Default | Description |
|---|---|---|
| `YOLO_MODEL_PATH` | `../detection/models/yolov8n.pt` | Path to the YOLOv8 model file |

---

## 6. Detection Engine — How It Works

The detection engine is in `services/rekognition_service.py`. It uses a **priority fallback chain**:

```
AWS Rekognition  →  if not available  →  YOLOv8  →  if not available  →  Demo Mode
```

The active mode is shown in the top-right badge on the dashboard (e.g., "YOLO Live" or "AWS Live").

### Mode 1: AWS Rekognition (Cloud)

When AWS credentials are set and valid, Rekognition runs **4 parallel API calls** per frame:

| API Call | What It Detects | Output |
|---|---|---|
| `detect_labels` | Objects, scenes (car, person, fire, etc.) | Label + bounding box + confidence |
| `detect_faces` | Human faces | Bounding box + emotion + estimated age |
| `detect_text` | Text/signs in the image (OCR) | Text string + bounding box |
| `detect_moderation_labels` | Unsafe/explicit content | Category label (e.g., "Explicit Nudity") |

### Mode 2: YOLOv8 (Local, Offline)

When AWS is not configured, YOLOv8 nano (`yolov8n.pt`) runs locally on your machine.

- Detects **80 object classes** from the COCO dataset
- Runs on CPU (no GPU required)
- Speed: ~50–200ms per frame on modern hardware
- Also runs **pytesseract OCR** for text detection if installed

### Mode 3: Demo Mode

When neither AWS nor YOLO is available, the system returns a fake "Person (DEMO)" detection with a bounding box so you can see the UI working.

### Unified Output Format

Regardless of which mode is active, every detection returns the same format:

```json
{
  "label":          "Person",
  "confidence":     87.5,
  "detection_type": "yolo",
  "bounding_box":   { "Left": 0.20, "Top": 0.10, "Width": 0.35, "Height": 0.70 },
  "color":          "#FF6B00",
  "is_alert":       true
}
```

- `bounding_box` values are **fractions of image size** (0.0 to 1.0), not pixels
- `is_alert` is `true` when label is in HIGH_THREAT_LABELS AND confidence ≥ 65%
- `color` is a hex code used to draw the bounding box in the browser

### Color Coding by Object Type

| Color | Objects |
|---|---|
| Orange `#FF6B00` | Person |
| Blue `#00B4FF` | Face |
| Green `#00E676` | Text, default |
| Red `#FF0000` | Knife, Gun, Moderation |
| Yellow `#FFD600` | Car, Truck, Bus |
| Purple `#CE93D8` | Cell phone, Laptop |

---

## 7. Alert System — SMS & Email

Alert logic lives in `services/alert_service.py`.

### Alert Flow

```
Detection result has is_alert = true
         ↓
confidence ≥ ALERT_CONFIDENCE_THRESHOLD (65%)?
         ↓  YES
Per-label cooldown has elapsed (default 30 sec)?
         ↓  YES
Save screenshot to snapshots/
         ↓
Write AlertEvent to database
         ↓
dispatch_alert() → starts background daemon thread
         ↓
Thread sends: SMS (Twilio) + Email (SMTP) simultaneously
```

### Per-Label Cooldown

The system prevents alert spam. After an alert fires for "Person", it will not fire again for "Person" for 30 seconds (configurable via `ALERT_COOLDOWN_SECONDS`). Each label has its own independent timer.

```python
# Each label has its own last-alert timestamp
_last = { "person": 1740000000.0, "knife": 1740000005.2 }
```

### SMS Message Format

```
ALERT: Person detected!
Confidence: 87%
Camera: webcam
Time: 2026-03-26 10:45:00 UTC
Check dashboard: http://localhost:5000
```

### Email

Sends an HTML-formatted email with:
- Object name, confidence, camera source, timestamp
- Screenshot of the frame attached as `alert.jpg`
- Dark-themed HTML design matching the dashboard

### Background Threading

`dispatch_alert()` always starts a **daemon thread** so the detection API response is not delayed waiting for Twilio/SMTP network calls.

---

## 8. All API Endpoints

All endpoints require login (`@login_required`). Unauthenticated requests are redirected to `/auth/login`.

### Authentication

| Method | URL | Description |
|---|---|---|
| GET/POST | `/auth/login` | Login form — accepts `username` + `password` |
| GET/POST | `/auth/register` | Register new account |
| GET | `/auth/logout` | Log out and clear session |
| GET | `/auth/me` | Returns 200 if session valid, 401 if expired |

### Dashboard

| Method | URL | Description |
|---|---|---|
| GET | `/dashboard` | Renders the main dashboard page |
| GET | `/api/stats` | Returns JSON for charts — called every 5 seconds by dashboard.js |

`/api/stats` response:
```json
{
  "summary": {
    "total_detections": 337,
    "total_alerts": 155,
    "alerts_today": 21,
    "alerts_last_hour": 4
  },
  "frequency": { "labels": ["00:00","01:00",...], "data": [5,12,...] },
  "top_labels": { "labels": ["person","car",...], "data": [120,30,...] },
  "recent_alerts": [...],
  "detection_mode": "yolo"
}
```

### Camera / Live Detection

| Method | URL | Description |
|---|---|---|
| POST | `/api/detect` | Main detection endpoint — receives base64 JPEG frame, returns detections |
| GET | `/api/rtsp/feed` | MJPEG stream from RTSP or any OpenCV-readable source |
| POST | `/api/snapshot` | Save current frame as a file without running detection |
| GET | `/api/status` | Health check — shows detection mode, thresholds |

`POST /api/detect` request body:
```json
{
  "frame": "data:image/jpeg;base64,/9j/4AAQ...",
  "camera_source": "webcam"
}
```

`POST /api/detect` response:
```json
{
  "detections": [
    {
      "label": "Person",
      "confidence": 87.5,
      "detection_type": "yolo",
      "bounding_box": { "Left": 0.2, "Top": 0.1, "Width": 0.35, "Height": 0.7 },
      "color": "#FF6B00",
      "is_alert": true
    }
  ],
  "alert_triggered": true,
  "detection_mode": "yolo",
  "count": 1
}
```

`GET /api/rtsp/feed?url=rtsp://...` — returns an MJPEG video stream with `Content-Type: multipart/x-mixed-replace`.

### Alerts

| Method | URL | Description |
|---|---|---|
| GET | `/alerts` | Renders the alerts page |
| GET | `/api/alerts` | Paginated alert list (query: `page`, `per_page`, `label`, `min_confidence`) |
| GET | `/api/alerts/<id>` | Get single alert by ID |
| DELETE | `/api/alerts/<id>` | Delete alert (admin only) |
| GET | `/api/alerts/summary` | Count of alerts in the last 5 minutes |

### Image Detection

| Method | URL | Description |
|---|---|---|
| GET | `/image-detection` | Renders the image upload page |
| POST | `/detect-image` | Upload image file → returns detection results (max 5MB) |

### Content Moderation

| Method | URL | Description |
|---|---|---|
| GET | `/moderation` | Renders moderation page |
| POST | `/verify-age` | Age verification gate (must be 18+) |
| POST | `/moderate-image` | Detect unsafe content in uploaded image |
| POST | `/moderate-video` | Analyze video for unsafe content (frame sampling or AWS async job) |

---

## 9. Database Models

Database file: `flask_rekognition/instance/surveillance.db`

### Table: `users`

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `username` | String(64), unique | Login username |
| `email` | String(120) | Optional email |
| `password_hash` | String(256) | Bcrypt-hashed password |
| `role` | String(16) | `admin` or `user` |
| `created_at` | DateTime | Account creation time (UTC) |

### Table: `alert_events`

Stores every alert that was triggered (when a threat was detected AND cooldown was clear).

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment |
| `object_detected` | String(128) | Label that triggered the alert (e.g., "Person") |
| `confidence_score` | Float | Detection confidence (0–100) |
| `detection_type` | String(32) | `yolo`, `rekognition`, `demo`, etc. |
| `camera_source` | String(256) | `webcam`, `rtsp`, `local` |
| `image_path` | String(512) | Path to saved screenshot (in `snapshots/`) |
| `alert_sent` | Boolean | Whether alert was dispatched |
| `sms_sent` | Boolean | Whether SMS was sent via Twilio |
| `timestamp` | DateTime (indexed) | When the alert happened (UTC) |

### Table: `detection_log`

Logs every single detection — even non-alert ones. Used for the dashboard charts.

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment |
| `label` | String(128), indexed | Detected object name |
| `confidence` | Float | Confidence score |
| `detection_type` | String(32) | Backend that detected it |
| `bounding_box` | String(256) | JSON string of bbox coordinates |
| `camera_source` | String(256) | Source of the frame |
| `timestamp` | DateTime (indexed) | Detection time (UTC) |

---

## 10. Frontend — Pages & UI

### Page 1: Dashboard (`/dashboard`)

The main page. Contains:

- **4 stat cards** (Total Detections, Total Alerts, Alerts Today, Last Hour) — updated every 5 seconds without page reload
- **Live Camera panel** — webcam/RTSP/local video feed with AI bounding box overlay
- **Detected Objects panel** — table showing current detections with type badges and confidence bars
- **Detected Text panel** — shows OCR results as chips
- **Detection Activity chart** — line chart of detections per hour over 24 hours
- **Top Objects chart** — doughnut chart of most frequently detected labels
- **Recent Alerts table** — last 10 alerts with timestamp, confidence, SMS status

### Page 2: Alerts (`/alerts`)

- Full paginated table of all alert events
- Filter by label name and minimum confidence
- Click any row to see full details
- Admin users can delete individual alerts

### Page 3: Image Detection (`/image-detection`)

- Upload a JPEG or PNG image (max 5MB)
- Click Analyze — runs the same detection engine
- Shows a labeled list of everything found
- Color-codes threats (red) vs safe objects (green) vs miscellaneous (orange)

### Page 4: Moderation (`/moderation`)

- Age-gated (18+ verification required)
- Upload image or video
- Runs AWS Rekognition content moderation
- Returns category labels like "Explicit Nudity", "Violence", "Drug Use"
- For videos: samples ~10 keyframes if no S3 bucket, or runs async AWS Video job with S3

---

## 11. Live Camera System — Deep Dive

The live camera is the core feature. Here is exactly how it works end to end.

### Input Sources

You can use any of three sources selected by the radio buttons:

| Source | How It Works |
|---|---|
| **Webcam** | Uses `navigator.mediaDevices.getUserMedia()` in the browser — accesses your device camera directly |
| **RTSP** | Enter an RTSP URL (e.g., `rtsp://admin:pass@192.168.1.100:554/stream`). The Flask backend opens it with OpenCV and streams MJPEG frames to the browser |
| **Local Video** | Pick an MP4/AVI file from your computer. Plays in the browser `<video>` element |

### Front / Rear Camera Toggle

A **"Rear ↺"** button appears in the webcam controls.

- Click once → switches to **Front Camera** (`facingMode: "user"`)
- Click again → switches back to **Rear Camera** (`facingMode: "environment"`)
- If the camera is already running, it restarts automatically with the new facing

This works on phones (front camera = selfie, rear = main), and on laptops it uses whichever camera is available.

### Two-Loop Architecture (Performance)

The camera system uses two completely separate loops:

**Loop 1 — Render Loop (`requestAnimationFrame`)**
- Runs at ~60 fps (matches your screen refresh rate)
- Reads from `lastDetections` cache
- Draws bounding boxes on the canvas overlay
- Never waits for the backend — always smooth

**Loop 2 — Detection Loop (`setInterval`, every 500ms)**
- Captures a JPEG frame from the video
- Sends it to `POST /api/detect`
- Updates `lastDetections` cache with the response
- Uses a `busy` flag — if the previous request is still in flight, skips this tick

This means **the bounding boxes never freeze** even when AWS Rekognition takes 1–2 seconds to respond. The boxes keep drawing at 60fps from the cache while waiting.

### Frame Capture

Each detection frame is:
1. Drawn onto a hidden off-screen canvas
2. Resized to max **640px wide** (maintains aspect ratio)
3. Encoded as JPEG at 75% quality
4. Converted to base64 string
5. Sent as JSON to `POST /api/detect`

### Bounding Box Drawing

The server returns bounding boxes as fractions (0.0–1.0). The canvas drawing code converts them to pixels:

```
pixel_x = bounding_box.Left  × canvas.width
pixel_y = bounding_box.Top   × canvas.height
pixel_w = bounding_box.Width × canvas.width
pixel_h = bounding_box.Height × canvas.height
```

Alert detections get a thick red glow outline. Normal detections get a 2px colored border.

### RTSP Streaming (Backend)

When RTSP mode is selected, the browser displays an `<img>` element. The `src` is set to `/api/rtsp/feed?url=...`.

The backend uses a **threaded capture** architecture:

1. `_ThreadedCap` starts a background daemon thread
2. The thread continuously calls `cap.read()` and puts frames into a queue (max size 2)
3. If the queue is full, old frames are discarded immediately (no lag buildup)
4. The main generator reads from the queue, skips every 2nd frame, resizes to 640px, encodes to JPEG, and yields MJPEG boundary blocks
5. The browser receives the continuous MJPEG stream and displays it as a live image

---

## 12. Real-Time Performance Architecture

### Why the Old System Was Slow

The original code had one `setInterval(detectFrame, 150ms)` loop that did everything — capture frame, call API, wait for response, draw boxes. If AWS took 1 second to respond, the canvas froze for 1 second.

Frame size was 200px wide — too small for accurate detection.

### What Was Optimized

| Issue | Before | After |
|---|---|---|
| Canvas framerate | Tied to API response (~1–5 fps) | Decoupled, runs at 60 fps via rAF |
| Detection interval | 150ms (too fast, causes queue) | 500ms (enough time for API round-trip) |
| Frame size | 200px (poor accuracy) | 640px (good accuracy) |
| RTSP blocking | `cap.read()` blocks generator | Background thread + non-blocking queue |
| RTSP lag | Frames accumulate | Queue capped at 2, old frames dropped |

### Performance Numbers (Typical)

| Scenario | Detection Speed | Canvas FPS |
|---|---|---|
| YOLO on CPU (laptop) | ~3–6 det/s | 60 fps |
| AWS Rekognition | ~1–2 det/s | 60 fps |
| Demo mode | ~10+ det/s | 60 fps |

The **det/s** counter shown in the camera feed is detection throughput (how fast the backend responds). The canvas always renders at 60fps regardless.

---

## 13. User Authentication & Roles

### Login

- URL: `/auth/login`
- Sessions are permanent (24 hours) — browser refresh does not log you out
- "Remember Me" checkbox extends session to 7 days (cookie-based)

### Registration

- URL: `/auth/register`
- Creates a new account with `role = "admin"` by default
- Passwords are hashed with `werkzeug.security.generate_password_hash` (pbkdf2:sha256)

### Default Admin

On first run (empty database), the app auto-creates:
- Username: `admin`
- Password: `Admin@1234`
- Role: `admin`

### Roles

| Role | Can Do |
|---|---|
| `admin` | Everything — including deleting alerts |
| `user` | View dashboard, view alerts, use camera and image detection |

---

## 14. Image Detection Page

URL: `/image-detection`

### How to Use

1. Click "Choose File" and select a JPEG or PNG image (max 5MB)
2. Click "Analyze"
3. The page shows a table of everything found

### Results Explained

| Column | Description |
|---|---|
| Name | What was detected (e.g., "Person", "Car", "Knife") |
| Confidence | How sure the AI is (0–100%) |
| Type | Which backend detected it (`yolo`, `rekognition`, `face`, `text`) |
| Threat? | Red badge = threat, Green = safe, Orange = miscellaneous |

A detection is marked as **Threat** if:
- It is in the HIGH_THREAT_LABELS list (weapon, knife, gun, fire, etc.) AND confidence ≥ 65%
- OR it is not in the safe-label whitelist AND confidence ≥ 65% (miscellaneous objects)

---

## 15. Content Moderation Page

URL: `/moderation`

### Age Gate

You must enter your date of birth and confirm you are 18+ before the moderation tools appear.

### Image Moderation

Upload an image. The system calls AWS Rekognition `detect_moderation_labels` and returns categories like:

- Explicit Nudity
- Violence
- Visually Disturbing
- Drug Use
- Tobacco
- Alcohol
- Gambling

Each result includes a confidence percentage.

### Video Moderation

Upload a video file:
- Without S3: extracts ~10 keyframes and runs image moderation on each
- With S3 configured: uploads video to S3, starts async Rekognition video job, polls for up to 2 minutes

---

## 16. Alerts Page

URL: `/alerts`

### Features

- Shows all alerts ever triggered in a paginated table (25 per page)
- Columns: ID, Object, Confidence, Camera Source, SMS Sent, Timestamp
- Filter by label name (e.g., type "person" to show only person alerts)
- Filter by minimum confidence (e.g., show only ≥ 80% alerts)
- Admin users can delete individual alerts with the trash icon

### Alert Count Badge

The navbar shows a badge with alerts from the last 5 minutes (calls `/api/alerts/summary`).

---

## 17. Data Flow — End to End

Here is the complete journey from a camera frame to an SMS on your phone:

```
[Your Camera]
     │
     │  getUserMedia() / RTSP / file
     ▼
[Browser — camera.js]
  requestAnimationFrame loop → renders bboxes from cache at 60fps
  setInterval loop (500ms)  → captures frame
     │
     │  JPEG frame resized to 640px
     │  Encoded as base64 string
     │  POST /api/detect   { "frame": "...", "camera_source": "webcam" }
     │
     ▼
[Flask — routes/camera.py — detect()]
  Decode base64 → raw bytes
     │
     ▼
[services/rekognition_service.py — detector.detect_all()]
  If AWS configured  → boto3 → detect_labels + faces + text + moderation
  Else if YOLO ready → ultralytics.YOLO → 80 classes
  Else               → demo fake detection
  Returns: [ {label, confidence, bounding_box, is_alert, ...} ]
     │
     ▼
[routes/camera.py — for each detection]
  Write DetectionLog to SQLite (every detection)
  If is_alert AND confidence ≥ 65% AND cooldown OK:
    Save screenshot to snapshots/
    Write AlertEvent to SQLite
    dispatch_alert() → start background thread
         │
         ▼
    [Background Thread — services/alert_service.py]
      send_sms()   → Twilio API → SMS to ADMIN_PHONE_NUMBER
      send_email() → Gmail SMTP → HTML email + screenshot attachment
     │
     ▼
[Flask response]
  { detections: [...], alert_triggered: true, count: 3 }
     │
     ▼
[Browser — camera.js]
  lastDetections = response.detections
  updateList()        → update detected objects table
  updateTextPanel()   → update OCR text chips
  if alert_triggered: flashAlert()  → red flash overlay
  renderFrame (rAF)   → drawBoxes(lastDetections) at 60fps
```

---

## 18. Common Errors & Fixes

### "Camera error: Permission denied"

**Cause:** Browser blocked camera access.

**Fix:**
- Chrome: Click the camera icon in the address bar → Allow
- Make sure site is accessed via `http://127.0.0.1:5000` not `http://localhost:5000` (some browsers treat them differently)
- On phones: HTTPS is required for camera access. Use a tunnel like ngrok.

---

### "RTSP connection failed"

**Cause:** The RTSP URL is wrong, camera is offline, or network blocks the port.

**Fix:**
- Test your URL in VLC Media Player first
- Common format: `rtsp://admin:password@192.168.1.100:554/stream1`
- Make sure Flask server and the IP camera are on the same network

---

### YOLOv8 model not found / "YOLO load failed"

**Cause:** The model file `yolov8n.pt` is missing from `detection/models/`.

**Fix:**
```python
# Run this once in Python to download the model
from ultralytics import YOLO
model = YOLO("yolov8n.pt")   # auto-downloads ~6MB
```
Or set `YOLO_MODEL_PATH=yolov8n.pt` in `.env` and let ultralytics download automatically on first run.

---

### "SMS failed: Unable to create record"

**Cause:** Twilio credentials are wrong, or the destination phone number is not verified on trial account.

**Fix:**
- On Twilio free trial: your destination phone number must be added to "Verified Caller IDs"
- Go to Twilio Console → Phone Numbers → Verified Caller IDs → Add your number

---

### "Email failed: Username and Password not accepted"

**Cause:** Gmail is blocking the login. You must use an **App Password**, not your regular Gmail password.

**Fix:**
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to App Passwords → Select app: Mail → Generate
4. Use the 16-character generated password in `.env` as `EMAIL_PASSWORD`

---

### Detection always shows "DEMO" mode

**Cause:** Neither AWS credentials nor YOLO are configured.

**Fix:**
- For YOLO (easiest): just install the dependencies — `pip install ultralytics opencv-python-headless` — YOLO auto-loads
- For AWS: add your credentials to `.env`

---

### Camera feed is black / video not showing

**Cause:** Video element not playing before detection starts.

**Fix:**
- Make sure you clicked **Start** (not just selected a source)
- For local video: the file must be an MP4/WebM format supported by the browser
- For webcam on mobile: only works over HTTPS or `localhost`

---

### Dashboard charts not updating

**Cause:** Dashboard.js polls `/api/stats` every 5 seconds. If session expired, it gets a 401.

**Fix:** Refresh the page — you will be redirected to login. After logging in, charts update again.

---

*Documentation generated for EyeQ v1.0 — Flask Rekognition Surveillance System*
*Last updated: 2026-03-26*
