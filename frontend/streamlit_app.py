"""
EYEQ – Streamlit Dashboard

Pages:
  1. Login
  2. Camera Control
  3. Live Detection
  4. Alert History
  5. System Status
"""

import time
import os
import sys
import requests
import base64
from datetime import datetime

import streamlit as st
import pandas as pd

# ── Resolve project root so imports work when launched from any cwd ──
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config.settings import APP_NAME, APP_VERSION

# ─── Page Config ───────────────────────────────────────────────

st.set_page_config(
    page_title=f"{APP_NAME} – Intelligent Vision Security",
    page_icon="👁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Constants ─────────────────────────────────────────────────

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
REFRESH_INTERVAL = 3   # seconds between live-feed refreshes


# ─── Session State Defaults ────────────────────────────────────

def _init_session():
    defaults = {
        "authenticated": False,
        "token": None,
        "username": None,
        "role": None,
        "page": "Login",
        "active_camera_source": None,
        "monitoring": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session()


# ─── API Helpers ───────────────────────────────────────────────

def _headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def _api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{path}", headers=_headers(), params=params, timeout=8)
        return r
    except requests.ConnectionError:
        st.error("Cannot connect to EYEQ API. Is the backend running?")
        return None


def _api_post(path: str, json: dict = None, data: dict = None):
    try:
        r = requests.post(f"{API_BASE}{path}", headers=_headers(), json=json, data=data, timeout=8)
        return r
    except requests.ConnectionError:
        st.error("Cannot connect to EYEQ API.")
        return None


def _api_delete(path: str):
    try:
        r = requests.delete(f"{API_BASE}{path}", headers=_headers(), timeout=8)
        return r
    except requests.ConnectionError:
        st.error("Cannot connect to EYEQ API.")
        return None


# ─── Global CSS ────────────────────────────────────────────────

st.markdown("""
<style>
    /* Sidebar nav */
    [data-testid="stSidebar"] { background: #0f1117; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: #1e2130;
        border-radius: 10px;
        padding: 12px 18px;
        border-left: 4px solid #e53935;
    }

    /* Alert table */
    .alert-row-suspicious { color: #ff5252; font-weight: bold; }

    /* Headings */
    h1, h2, h3 { color: #e53935; }

    div.stButton > button {
        background-color: #e53935;
        color: white;
        border: none;
        border-radius: 6px;
    }
    div.stButton > button:hover { background-color: #c62828; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: LOGIN
# ═══════════════════════════════════════════════════════════════

def page_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<h1 style='text-align:center;'>👁 EYEQ</h1>"
            "<p style='text-align:center;color:#aaa;'>Intelligent Vision Security System</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        tab_login, tab_register = st.tabs(["Login", "Register"])

        # ── Login ─────────────────────────────────────────────
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.warning("Please enter username and password.")
                else:
                    try:
                        r = requests.post(
                            f"{API_BASE}/auth/login",
                            data={"username": username, "password": password},
                            timeout=8,
                        )
                        if r.status_code == 200:
                            data = r.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.authenticated = True
                            # Fetch user info
                            me = requests.get(
                                f"{API_BASE}/auth/me",
                                headers={"Authorization": f"Bearer {data['access_token']}"},
                                timeout=8,
                            ).json()
                            st.session_state.username = me["username"]
                            st.session_state.role = me["role"]
                            st.session_state.page = "Dashboard"
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Login failed."))
                    except requests.ConnectionError:
                        st.error("Cannot reach EYEQ API. Ensure the backend is running.")

        # ── Register ──────────────────────────────────────────
        with tab_register:
            with st.form("reg_form"):
                new_user = st.text_input("New Username")
                new_pass = st.text_input("Password (min 8 chars)", type="password")
                new_role = st.selectbox("Role", ["user", "admin"])
                reg_btn = st.form_submit_button("Create Account", use_container_width=True)

            if reg_btn:
                if len(new_pass) < 8:
                    st.warning("Password must be at least 8 characters.")
                else:
                    try:
                        r = requests.post(
                            f"{API_BASE}/auth/register",
                            json={"username": new_user, "password": new_pass, "role": new_role},
                            timeout=8,
                        )
                        if r.status_code == 201:
                            st.success("Account created! Please log in.")
                        else:
                            st.error(r.json().get("detail", "Registration failed."))
                    except requests.ConnectionError:
                        st.error("Cannot reach EYEQ API.")


# ═══════════════════════════════════════════════════════════════
# SIDEBAR (authenticated)
# ═══════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown(f"## 👁 {APP_NAME} v{APP_VERSION}")
        st.markdown(f"**User:** {st.session_state.username}  \n**Role:** `{st.session_state.role}`")
        st.divider()

        pages = ["Dashboard", "Camera Control", "Live Detection", "Alert History", "System Status"]
        for p in pages:
            if st.button(p, key=f"nav_{p}", use_container_width=True):
                st.session_state.page = p
                st.rerun()

        st.divider()
        if st.button("Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# PAGE: DASHBOARD (overview)
# ═══════════════════════════════════════════════════════════════

def page_dashboard():
    st.title("EYEQ Dashboard")
    st.markdown("Real-time overview of your surveillance system.")

    # Fetch data
    alerts_resp = _api_get("/alerts", {"limit": 200})
    cameras_resp = _api_get("/cameras/")

    alerts = alerts_resp.json() if alerts_resp and alerts_resp.ok else []
    cameras = cameras_resp.json() if cameras_resp and cameras_resp.ok else []

    active_cameras = sum(1 for c in cameras if c.get("is_active"))

    # ── KPI Metrics ──────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Alerts", len(alerts))
    c2.metric("Cameras Registered", len(cameras))
    c3.metric("Cameras Active", active_cameras)
    today_alerts = sum(
        1 for a in alerts
        if a.get("timestamp", "").startswith(datetime.utcnow().strftime("%Y-%m-%d"))
    )
    c4.metric("Alerts Today", today_alerts)

    st.divider()

    # ── Recent Alerts Table ──────────────────────────────────
    st.subheader("Recent Alerts")
    if alerts:
        df = pd.DataFrame(alerts[:20])[["id", "detection_label", "confidence", "camera_source", "timestamp"]]
        df.columns = ["ID", "Label", "Confidence", "Camera", "Timestamp"]
        df["Confidence"] = df["Confidence"].apply(lambda x: f"{x:.0%}" if x else "—")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No alerts recorded yet.")

    # ── Camera Status ────────────────────────────────────────
    st.subheader("Camera Status")
    if cameras:
        for cam in cameras:
            status_icon = "🟢" if cam["is_active"] else "🔴"
            st.markdown(f"{status_icon} **{cam['camera_name']}** — `{cam['camera_source']}`")
    else:
        st.info("No cameras configured.")


# ═══════════════════════════════════════════════════════════════
# BROWSER CAMERA COMPONENT (WebRTC – works on desktop + mobile)
# ═══════════════════════════════════════════════════════════════

def _browser_camera_component(facing_mode: str = "environment", height: int = 480):
    """
    Injects an HTML5 getUserMedia video stream directly into the page.
    facing_mode:
        'user'        → front camera (selfie)
        'environment' → back camera (rear)
        'default'     → OS default / external webcam
    Returns a base64-encoded JPEG of the latest frame via Streamlit component value.
    """
    import streamlit.components.v1 as components

    constraints = (
        "{ video: { facingMode: 'user' } }"        if facing_mode == "user"
        else "{ video: { facingMode: 'environment' } }" if facing_mode == "environment"
        else "{ video: true }"
    )

    html_code = f"""
    <style>
      body {{ margin:0; background:#0f1117; }}
      #camWrap {{ position:relative; width:100%; max-width:720px; margin:auto; }}
      video {{ width:100%; border-radius:10px; border:2px solid #e53935; }}
      canvas {{ display:none; }}
      #status {{ color:#aaa; font-family:Arial; font-size:13px; margin:6px 0; text-align:center; }}
      #camLabel {{ position:absolute; top:10px; left:14px;
                   background:rgba(229,57,53,0.85); color:#fff;
                   padding:3px 10px; border-radius:4px; font-size:12px; font-family:Arial; }}
      .btn {{ background:#e53935; color:#fff; border:none; padding:8px 18px;
              border-radius:6px; cursor:pointer; font-size:13px; margin:4px; }}
      .btn:hover {{ background:#c62828; }}
    </style>

    <div id="camWrap">
      <video id="vid" autoplay playsinline muted></video>
      <span id="camLabel">EYEQ LIVE</span>
    </div>
    <canvas id="snap"></canvas>
    <p id="status">Requesting camera access...</p>
    <div style="text-align:center;">
      <button class="btn" onclick="switchCam('user')">Front Camera</button>
      <button class="btn" onclick="switchCam('environment')">Back Camera</button>
      <button class="btn" onclick="switchCam('default')">External / Default</button>
    </div>

    <script>
      let currentStream = null;

      async function startCamera(facingMode) {{
        const vid = document.getElementById('vid');
        const status = document.getElementById('status');
        if (currentStream) {{ currentStream.getTracks().forEach(t => t.stop()); }}

        let constraints = facingMode === 'default'
          ? {{ video: true }}
          : {{ video: {{ facingMode: facingMode }} }};

        try {{
          currentStream = await navigator.mediaDevices.getUserMedia(constraints);
          vid.srcObject = currentStream;
          const track = currentStream.getVideoTracks()[0];
          const settings = track.getSettings();
          status.textContent = 'Camera: ' + (track.label || facingMode)
            + ' | ' + (settings.width||'?') + 'x' + (settings.height||'?');
        }} catch(err) {{
          status.textContent = 'Camera error: ' + err.message;
          // Fallback: try any available camera
          if (facingMode !== 'default') {{
            try {{
              currentStream = await navigator.mediaDevices.getUserMedia({{ video: true }});
              vid.srcObject = currentStream;
              status.textContent = 'Fallback camera active';
            }} catch(e) {{ status.textContent = 'No camera available: ' + e.message; }}
          }}
        }}
      }}

      function switchCam(mode) {{ startCamera(mode); }}

      // Auto-start with requested facing mode
      startCamera('{facing_mode}');
    </script>
    """
    components.html(html_code, height=height + 80, scrolling=False)


# ═══════════════════════════════════════════════════════════════
# PAGE: CAMERA CONTROL
# ═══════════════════════════════════════════════════════════════

def page_camera_control():
    st.title("Camera Control Panel")

    # ── Live Browser Camera Preview ───────────────────────────
    st.subheader("Live Camera Preview")
    st.caption("Opens your device camera directly in the browser. Works on desktop, mobile (front & back), and external USB cameras.")

    col_front, col_back, col_ext = st.columns(3)
    facing = "environment"   # default = back/external
    if col_front.button("Front Camera", use_container_width=True):
        st.session_state["cam_facing"] = "user"
    if col_back.button("Back Camera", use_container_width=True):
        st.session_state["cam_facing"] = "environment"
    if col_ext.button("External / Default", use_container_width=True):
        st.session_state["cam_facing"] = "default"

    facing = st.session_state.get("cam_facing", "environment")
    _browser_camera_component(facing_mode=facing, height=420)

    st.divider()

    # ── Register Camera for AI Detection ─────────────────────
    st.subheader("Register Camera for AI Detection")
    st.caption("Register a source below to run YOLOv8 detection on it via the Live Detection page.")

    tab_web, tab_ip, tab_file = st.tabs(["Webcam / USB", "IP / RTSP", "Video File"])

    with tab_web:
        with st.form("add_webcam"):
            name = st.text_input("Camera Name", value="Webcam", placeholder="My Webcam")
            index = st.number_input("Device Index", min_value=0, max_value=20, value=0,
                                    help="0 = default webcam, 1 = second camera, etc.")
            if st.form_submit_button("Register Webcam", use_container_width=True):
                _register_camera(name, str(index))

    with tab_ip:
        with st.form("add_ip"):
            name = st.text_input("Camera Name", value="IP Camera", placeholder="Gate Camera")
            rtsp = st.text_input("RTSP / HTTP URL",
                                  placeholder="rtsp://admin:pass@192.168.1.100:554/stream1")
            if st.form_submit_button("Register IP Camera", use_container_width=True):
                _register_camera(name, rtsp)

    with tab_file:
        with st.form("add_file"):
            name = st.text_input("Camera Name", value="Video File", placeholder="CCTV Recording")
            path = st.text_input("File Path", placeholder="C:/videos/recording.mp4")
            if st.form_submit_button("Register Video File", use_container_width=True):
                _register_camera(name, path)

    st.divider()

    # ── Registered Cameras List ───────────────────────────────
    st.subheader("Registered Cameras")
    cameras_resp = _api_get("/cameras/")
    cameras = cameras_resp.json() if cameras_resp and cameras_resp.ok else []

    if not cameras:
        st.info("No cameras registered yet.")
        return

    for cam in cameras:
        with st.container():
            cols = st.columns([2, 3, 1, 1, 1, 1])
            cols[0].write(f"**{cam['camera_name']}**")
            cols[1].code(cam["camera_source"])
            cols[2].write("🟢 Active" if cam["is_active"] else "🔴 Idle")

            if cols[3].button("Start", key=f"start_{cam['id']}"):
                r = _api_post(f"/cameras/{cam['id']}/start")
                if r and r.ok:
                    st.session_state.active_camera_source = cam["camera_source"]
                    st.session_state.monitoring = True
                    st.session_state.page = "Live Detection"
                    st.rerun()

            if cols[4].button("Stop", key=f"stop_{cam['id']}"):
                r = _api_post(f"/cameras/{cam['id']}/stop")
                if r and r.ok:
                    st.session_state.monitoring = False
                    st.rerun()

            if cols[5].button("Del", key=f"del_{cam['id']}"):
                r = _api_delete(f"/cameras/{cam['id']}")
                if r and r.status_code == 204:
                    st.rerun()
        st.divider()


def _register_camera(name: str, source: str):
    """Helper to register a camera via API and show result."""
    if not name or not source:
        st.warning("Please fill in both fields.")
        return
    r = _api_post("/cameras/", json={"camera_name": name, "camera_source": source})
    if r and r.status_code == 201:
        st.success(f"Camera '{name}' registered successfully.")
        st.rerun()
    elif r:
        st.error(r.json().get("detail", "Failed to register camera."))


# ═══════════════════════════════════════════════════════════════
# PAGE: LIVE DETECTION
# ═══════════════════════════════════════════════════════════════

def page_live_detection():
    st.title("Live Detection View")

    st.info(
        "Choose a source below. **Browser Camera** uses your device directly (no install needed). "
        "**AI Detection** runs YOLOv8 on webcam/IP/file sources server-side."
    )

    mode = st.radio(
        "Detection Mode",
        ["Browser Camera (Live Preview)", "AI Detection (YOLOv8)", "Snapshot Detection"],
        horizontal=True,
    )

    # ── MODE 1: Browser Camera (pure WebRTC, no AI) ───────────
    if mode == "Browser Camera (Live Preview)":
        st.subheader("Browser Camera – Live Feed")
        st.caption("Works on any device: desktop, Android, iPhone. No server processing.")

        c1, c2, c3 = st.columns(3)
        if c1.button("Front Camera", use_container_width=True):
            st.session_state["live_facing"] = "user"
        if c2.button("Back Camera", use_container_width=True):
            st.session_state["live_facing"] = "environment"
        if c3.button("External / USB", use_container_width=True):
            st.session_state["live_facing"] = "default"

        facing = st.session_state.get("live_facing", "environment")
        _browser_camera_component(facing_mode=facing, height=500)

    # ── MODE 2: AI Detection (server-side YOLOv8) ─────────────
    elif mode == "AI Detection (YOLOv8)":
        st.subheader("AI Detection – YOLOv8")

        source_type = st.selectbox(
            "Camera Source",
            ["Webcam (index)", "IP / RTSP Camera", "Upload Video File"],
        )

        camera_source = None

        if source_type == "Webcam (index)":
            cam_index = st.number_input("Device Index", min_value=0, max_value=20, value=0)
            camera_source = int(cam_index)

        elif source_type == "IP / RTSP Camera":
            rtsp_url = st.text_input("RTSP URL", placeholder="rtsp://user:pass@192.168.1.x:554/stream")
            camera_source = rtsp_url if rtsp_url else None

        else:
            uploaded = st.file_uploader("Upload Video", type=["mp4", "avi", "mov", "mkv"])
            if uploaded:
                import tempfile
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                tmp.write(uploaded.read())
                tmp.close()
                camera_source = tmp.name

        col_run, col_stop = st.columns(2)
        if col_run.button("Start AI Detection", disabled=camera_source is None):
            st.session_state.monitoring = True
            st.session_state.active_camera_source = camera_source
        if col_stop.button("Stop"):
            st.session_state.monitoring = False

        if st.session_state.monitoring and camera_source is not None:
            import cv2
            try:
                from detection.detector import EYEQDetector
            except ImportError as ie:
                st.error(f"Detection module error: {ie}")
                return

            frame_ph = st.empty()
            info_ph  = st.empty()
            detector = EYEQDetector()
            src = int(camera_source) if isinstance(camera_source, int) else camera_source
            cap = cv2.VideoCapture(src)

            if not cap.isOpened():
                st.error(f"Cannot open source: {camera_source}")
                st.session_state.monitoring = False
                return

            for _ in range(90):
                if not st.session_state.monitoring:
                    break
                ret, frame = cap.read()
                if not ret:
                    break
                result = detector.process_frame(frame, camera_source=str(camera_source))
                _, jpeg = cv2.imencode(".jpg", result.frame)
                frame_ph.image(jpeg.tobytes(), channels="BGR", use_container_width=True)

                if result.has_alert:
                    info_ph.error(
                        f"ALERT: {', '.join(d.label for d in result.detections if d.is_suspicious)}"
                    )
                elif result.detections:
                    info_ph.info(
                        "Detected: " + ", ".join(f"{d.label} ({d.confidence:.0%})" for d in result.detections)
                    )
                else:
                    info_ph.empty()
                time.sleep(0.03)

            cap.release()
            if st.session_state.monitoring:
                st.rerun()
        else:
            st.info("Select a source and click **Start AI Detection**.")

    # ── MODE 3: Snapshot Detection ────────────────────────────
    else:
        st.subheader("Snapshot Detection")
        st.caption("Take a photo with your device camera and run AI detection on it instantly.")

        # ── YOLO status banner ────────────────────────────────
        try:
            from ultralytics import YOLO as _YOLO
            import os as _os
            _model_path = "detection/models/yolov8n.pt"
            if _os.path.exists(_model_path):
                st.success("YOLOv8 model loaded — AI detection is ACTIVE")
            else:
                st.warning(
                    "Model file not found at `detection/models/yolov8n.pt`. "
                    "Run in terminal: `python -c \"from ultralytics import YOLO; YOLO('yolov8n.pt')\"` "
                    "then move `yolov8n.pt` to `detection/models/`"
                )
        except ImportError:
            st.error(
                "ultralytics not installed — running in DEMO mode (no detections). "
                "Fix: `python -m pip install ultralytics torch torchvision "
                "--index-url https://download.pytorch.org/whl/cpu`"
            )

        snap = st.camera_input("Take a photo (uses your device camera — front/back auto-selected)")
        if snap:
            import cv2, numpy as np
            from PIL import Image
            import io
            try:
                from detection.detector import EYEQDetector, YOLO_AVAILABLE
            except ImportError:
                st.error("ultralytics not installed. Run: python -m pip install ultralytics")
                return

            if not YOLO_AVAILABLE:
                st.error("YOLO not available. Install ultralytics first (see banner above).")
                return

            img = Image.open(io.BytesIO(snap.getvalue())).convert("RGB")
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            with st.spinner("Running YOLOv8 AI detection..."):
                detector = EYEQDetector()
                result = detector.process_frame(frame, camera_source="snapshot")

            _, jpeg = cv2.imencode(".jpg", result.frame)
            st.image(jpeg.tobytes(), caption="Detection Result", use_container_width=True)

            if result.detections:
                st.subheader(f"Detected {len(result.detections)} object(s)")
                rows = [
                    {
                        "Label": d.label,
                        "Confidence": f"{d.confidence:.0%}",
                        "Suspicious": "⚠ YES" if d.is_suspicious else "No",
                        "BBox (x1,y1,x2,y2)": str(d.bbox),
                    }
                    for d in result.detections
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                if result.has_alert:
                    st.error("SUSPICIOUS OBJECT DETECTED — Alert has been logged.")
            else:
                st.warning(
                    "No objects detected. Try: better lighting, hold object closer, "
                    "or lower DETECTION_CONFIDENCE in config/settings.py (currently 0.25)."
                )


# ═══════════════════════════════════════════════════════════════
# PAGE: ALERT HISTORY
# ═══════════════════════════════════════════════════════════════

def page_alert_history():
    st.title("Alert History")

    col_limit, col_refresh = st.columns([3, 1])
    limit = col_limit.slider("Show last N alerts", 10, 500, 100)
    if col_refresh.button("Refresh"):
        st.rerun()

    alerts_resp = _api_get("/alerts", {"limit": limit})
    if not alerts_resp or not alerts_resp.ok:
        st.error("Failed to fetch alerts.")
        return

    alerts = alerts_resp.json()
    if not alerts:
        st.info("No alerts recorded yet.")
        return

    df = pd.DataFrame(alerts)
    df["confidence"] = df["confidence"].apply(lambda x: f"{x:.0%}" if x else "—")

    # Colour suspicious labels
    st.dataframe(
        df[["id", "detection_label", "confidence", "camera_source", "timestamp", "image_path"]].rename(
            columns={
                "id": "ID",
                "detection_label": "Label",
                "confidence": "Confidence",
                "camera_source": "Camera",
                "timestamp": "Timestamp",
                "image_path": "Screenshot",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Screenshot viewer
    st.subheader("Screenshot Viewer")
    selected_id = st.selectbox("Select Alert ID to view screenshot", [a["id"] for a in alerts])
    selected = next((a for a in alerts if a["id"] == selected_id), None)
    if selected and selected.get("image_path") and os.path.isfile(selected["image_path"]):
        st.image(selected["image_path"], caption=f"Alert #{selected_id} – {selected['detection_label']}")
    else:
        st.info("No screenshot available for this alert.")


# ═══════════════════════════════════════════════════════════════
# PAGE: SYSTEM STATUS
# ═══════════════════════════════════════════════════════════════

def page_system_status():
    st.title("System Status")

    # API health
    try:
        health = requests.get(f"{API_BASE}/health", timeout=4)
        if health.ok:
            data = health.json()
            st.success(f"API: {data.get('status', 'ok').upper()} — {data.get('app')} v{data.get('version')}")
        else:
            st.error("API returned an error.")
    except Exception:
        st.error("API is unreachable.")

    st.divider()
    st.subheader("Configuration")
    from config import settings
    config_data = {
        "App": settings.APP_NAME,
        "Version": settings.APP_VERSION,
        "Debug": str(settings.DEBUG),
        "YOLO Model": settings.YOLO_MODEL_PATH,
        "Detection Confidence": f"{settings.DETECTION_CONFIDENCE:.0%}",
        "Alert Cooldown (s)": str(settings.ALERT_COOLDOWN_SECONDS),
        "Frame Skip": str(settings.FRAME_SKIP),
        "DB URL": settings.DATABASE_URL[:40] + "..." if len(settings.DATABASE_URL) > 40 else settings.DATABASE_URL,
        "SMS Configured": "Yes" if settings.TWILIO_ACCOUNT_SID else "No",
        "Email Configured": "Yes" if settings.EMAIL_ADDRESS else "No",
    }
    st.table(pd.DataFrame(config_data.items(), columns=["Setting", "Value"]))

    st.divider()
    st.subheader("Suspicious Labels Monitored")
    st.write(", ".join(sorted(settings.SUSPICIOUS_LABELS)))


# ═══════════════════════════════════════════════════════════════
# MAIN ROUTER
# ═══════════════════════════════════════════════════════════════

def main():
    if not st.session_state.authenticated:
        page_login()
        return

    render_sidebar()

    page = st.session_state.page
    if page == "Dashboard":
        page_dashboard()
    elif page == "Camera Control":
        page_camera_control()
    elif page == "Live Detection":
        page_live_detection()
    elif page == "Alert History":
        page_alert_history()
    elif page == "System Status":
        page_system_status()
    else:
        page_dashboard()


if __name__ == "__main__":
    main()
