/**
 * camera.js
 *
 * Supports three input sources:
 *   webcam  → getUserMedia → capture JPEG frame → POST /api/detect
 *   rtsp    → server MJPEG stream (/api/rtsp/feed) → capture from <img> → POST /api/detect
 *   local   → <input type="file"> video → capture frame → POST /api/detect
 */
(function () {
  "use strict";

  const video = document.getElementById("videoFeed");
  const rtspImg = document.getElementById("rtspFeed");
  const canvas = document.getElementById("bbox");
  const btnStart = document.getElementById("btnStart");
  const btnStop = document.getElementById("btnStop");
  const btnSnap = document.getElementById("btnSnap");
  const camSel = document.getElementById("camSelect");
  const fpsEl = document.getElementById("fpsText");
  const flash = document.getElementById("alertFlash");
  const detList  = document.getElementById("detList");
  const detCount = document.getElementById("detCount");
  const textPanel = document.getElementById("textPanel");
  const textCount = document.getElementById("textCount");
  const textEmpty = document.getElementById("textEmpty");

  const webcamControls = document.getElementById("webcamControls");
  const rtspControls = document.getElementById("rtspControls");
  const localControls = document.getElementById("localControls");
  const rtspUrlInput = document.getElementById("rtspUrl");
  const localFileInput = document.getElementById("localFile");

  if (!video) return;

  const ctx = canvas.getContext("2d");
  const offCtx = document.createElement("canvas").getContext("2d");

  let stream = null;
  let timer = null;
  let busy = false;
  let activeSource = "webcam";
  let fCount = 0,
    fTime = Date.now();

  const INTERVAL = 150; // ms between detection attempts (busy-flag prevents overlap)
  const MAX_W = 200; // smaller frame = faster encode + transfer + inference
  const QUALITY = 0.65;

  // ── Source radio toggle ─────────────────────────────────────────
  document.querySelectorAll('input[name="inputSource"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      activeSource = radio.value;
      webcamControls.classList.toggle("d-none", activeSource !== "webcam");
      rtspControls.classList.toggle("d-none", activeSource !== "rtsp");
      localControls.classList.toggle("d-none", activeSource !== "local");
    });
  });

  // ── Button wiring ───────────────────────────────────────────────
  btnStart.addEventListener("click", start);
  btnStop.addEventListener("click", stop);
  btnSnap.addEventListener("click", snapshot);

  // ── Start ───────────────────────────────────────────────────────
  async function start() {
    switch (activeSource) {
      case "webcam":
        await startWebcam();
        break;
      case "rtsp":
        startRtsp();
        break;
      case "local":
        startLocal();
        break;
    }
  }

  async function startWebcam() {
    const facing = camSel ? camSel.value : "environment";
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: facing },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      showEl("video");
      onStarted();
    } catch (e) {
      setStatus("Camera error: " + e.message, "text-danger");
    }
  }

  function startRtsp() {
    const url = rtspUrlInput ? rtspUrlInput.value.trim() : "";
    if (!url) {
      setStatus("Enter an RTSP URL first.", "text-warning");
      return;
    }
    rtspImg.src = "/api/rtsp/feed?url=" + encodeURIComponent(url);
    rtspImg.onerror = () => setStatus("RTSP connection failed", "text-danger");
    showEl("rtsp");
    onStarted();
  }

  function startLocal() {
    const file = localFileInput && localFileInput.files[0];
    if (!file) {
      setStatus("Select a video file first.", "text-warning");
      return;
    }
    video.src = URL.createObjectURL(file);
    video.loop = true;
    video.play().catch(() => {});
    showEl("video");
    onStarted();
  }

  function onStarted() {
    btnStart.disabled = true;
    btnStop.disabled = false;
    document.getElementById("cameraWrapper").classList.add("camera-active");
    setStatus("Detecting…", "text-success");
    timer = setInterval(detectFrame, INTERVAL);
  }

  // ── Stop ────────────────────────────────────────────────────────
  function stop() {
    clearInterval(timer);
    timer = null;
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
    video.srcObject = null;
    video.src = "";
    rtspImg.src = "";
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    btnStart.disabled = false;
    btnStop.disabled = true;
    fpsEl.textContent = "";
    document.getElementById("cameraWrapper").classList.remove("camera-active");
    setStatus("Camera stopped — click Start", "text-muted");
    detList.innerHTML =
      '<tr><td colspan="4" class="text-muted text-center py-3">Camera stopped</td></tr>';
    detCount.textContent = "0";
    updateTextPanel([]);
  }

  // ── Detect ──────────────────────────────────────────────────────
  async function detectFrame() {
    if (busy) return;
    if (activeSource === "rtsp" && !rtspImg.naturalWidth) return;
    if (activeSource !== "rtsp" && !video.videoWidth) return;

    busy = true;
    try {
      const b64 = captureFrame();
      const res = await fetch("/api/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ frame: b64, camera_source: activeSource }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();

      drawBoxes(data.detections || []);
      updateList(data.detections || []);
      updateTextPanel(data.detections || []);
      if (data.alert_triggered) flashAlert();
      updateFps();
      setStatus(
        `Detecting… (${data.detection_mode || "yolo"})`,
        "text-success",
      );
    } catch (e) {
      setStatus("Error: " + e.message, "text-warning");
    } finally {
      busy = false;
    }
  }

  function captureFrame() {
    const src = activeSource === "rtsp" ? rtspImg : video;
    const vw =
      activeSource === "rtsp" ? rtspImg.naturalWidth : video.videoWidth;
    const vh =
      activeSource === "rtsp" ? rtspImg.naturalHeight : video.videoHeight;
    const scale = Math.min(1, MAX_W / vw);
    const c = offCtx.canvas;
    c.width = Math.floor(vw * scale);
    c.height = Math.floor(vh * scale);
    offCtx.drawImage(src, 0, 0, c.width, c.height);
    return c.toDataURL("image/jpeg", QUALITY);
  }

  // ── Drawing ─────────────────────────────────────────────────────
  function drawBoxes(detections) {
    const ref = activeSource === "rtsp" ? rtspImg : video;
    const rect = ref.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    detections.forEach((det) => {
      const bb = det.bounding_box;
      if (!bb) return;
      const x = bb.Left * canvas.width,
        y = bb.Top * canvas.height;
      const w = bb.Width * canvas.width,
        h = bb.Height * canvas.height;
      const color = det.color || "#00e676";

      ctx.strokeStyle = color;
      ctx.lineWidth = det.is_alert ? 3 : 2;
      ctx.strokeRect(x, y, w, h);

      const lbl = `${det.label} ${det.confidence.toFixed(0)}%`;
      const fontSize = Math.max(11, canvas.width * 0.017);
      ctx.font = `bold ${fontSize}px Arial, sans-serif`;
      const tw = ctx.measureText(lbl).width + 8,
        th = fontSize + 7;
      ctx.fillStyle = color;
      ctx.fillRect(x, y - th, tw, th);
      ctx.fillStyle = "#000";
      ctx.fillText(lbl, x + 4, y - 4);

      if (det.is_alert) {
        ctx.strokeStyle = "rgba(255,0,0,0.4)";
        ctx.lineWidth = 8;
        ctx.strokeRect(x - 3, y - 3, w + 6, h + 6);
      }
    });
  }

  function updateList(detections) {
    detCount.textContent = detections.filter((d) => d.bounding_box).length;
    if (!detections.length) {
      detList.innerHTML =
        '<tr><td colspan="4" class="text-muted text-center">Nothing detected</td></tr>';
      return;
    }
    const typeColors = {
      yolo: "#1d4ed8",
      label: "#1e40af",
      face: "#0369a1",
      text: "#15803d",
      moderation: "#b91c1c",
      demo: "#78350f",
    };
    detList.innerHTML = detections
      .map((d) => {
        const bg = typeColors[d.detection_type] || "#334155";
        const conf = d.confidence.toFixed(0);
        return `<tr ${d.is_alert ? 'style="background:rgba(239,68,68,.12);"' : ""}>
        <td class="fw-semibold">${d.label}</td>
        <td><span class="badge" style="background:${bg};">${d.detection_type}</span></td>
        <td>
          <div class="d-flex align-items-center gap-1">
            <div style="width:55px;height:5px;background:#1e293b;border-radius:3px;overflow:hidden;">
              <div style="width:${conf}%;height:100%;background:${d.color || "#00e676"};border-radius:3px;"></div>
            </div>
            <small>${conf}%</small>
          </div>
        </td>
        <td>${d.is_alert ? "&#9888;" : "—"}</td>
      </tr>`;
      })
      .join("");
  }

  function updateTextPanel(detections) {
    if (!textPanel) return;
    const texts = detections.filter(d => d.detection_type === "text");
    if (textCount) textCount.textContent = texts.length;

    if (!texts.length) {
      if (textEmpty) textEmpty.style.display = "";
      // Remove any existing chips
      textPanel.querySelectorAll(".text-chip").forEach(c => c.remove());
      return;
    }

    if (textEmpty) textEmpty.style.display = "none";
    // Remove stale chips then re-render
    textPanel.querySelectorAll(".text-chip").forEach(c => c.remove());
    texts.forEach(d => {
      // Strip surrounding  Text: "…"  wrapper
      const raw = d.label.replace(/^Text:\s*"(.+)"$/, "$1");
      const chip = document.createElement("span");
      chip.className = "text-chip";
      chip.style.cssText = `
        background:rgba(0,230,118,.1);border:1px solid rgba(0,230,118,.25);
        color:#00e676;font-size:.75rem;padding:3px 10px;border-radius:20px;
        font-family:monospace;letter-spacing:.3px;
        display:inline-flex;align-items:center;gap:6px;`;
      chip.innerHTML =
        `<i class="bi bi-fonts" style="font-size:.7rem;"></i>${raw}` +
        `<span style="color:rgba(0,230,118,.5);font-size:.68rem;">${d.confidence.toFixed(0)}%</span>`;
      textPanel.appendChild(chip);
    });
  }

  function flashAlert() {
    flash.classList.remove("d-none", "pulse-anim");
    void flash.offsetWidth;
    flash.classList.add("pulse-anim");
    setTimeout(() => flash.classList.add("d-none"), 4000);
  }

  function updateFps() {
    fCount++;
    const now = Date.now();
    if (now - fTime >= 3000) {
      fpsEl.textContent = (fCount / ((now - fTime) / 1000)).toFixed(1) + " fps";
      fCount = 0;
      fTime = now;
    }
  }

  async function snapshot() {
    const ok =
      activeSource === "rtsp" ? rtspImg.naturalWidth > 0 : video.videoWidth > 0;
    if (!ok) {
      alert("Start the camera first.");
      return;
    }
    try {
      await fetch("/api/snapshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ frame: captureFrame() }),
      });
      toast("Snapshot saved!", "success");
    } catch (e) {
      toast("Snapshot failed.", "danger");
    }
  }

  function showEl(which) {
    video.classList.toggle("d-none", which !== "video");
    rtspImg.classList.toggle("d-none", which !== "rtsp");
  }

  function setStatus(msg, cls) {
    const el = document.getElementById("camStatus");
    el.textContent = msg;
    el.className = cls || "text-muted";
  }

  function toast(msg, type = "info") {
    const t = document.createElement("div");
    t.className = `alert alert-${type} position-fixed bottom-0 end-0 m-3 shadow`;
    t.style.zIndex = 9999;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
  }
})();
