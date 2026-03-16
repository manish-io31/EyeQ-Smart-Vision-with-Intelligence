/**
 * camera.js
 *
 * Flow:
 *   getUserMedia → <video> → every 1.5 s capture JPEG frame →
 *   POST /api/detect (base64) → JSON detections →
 *   draw bounding boxes on <canvas> overlay (like the screenshot)
 *
 * Bounding box format from server:
 *   { Left, Top, Width, Height }  — all 0-1 fractions of image size
 */
(function () {
  'use strict';

  const video   = document.getElementById('videoFeed');
  const canvas  = document.getElementById('bbox');
  const btnStart= document.getElementById('btnStart');
  const btnStop = document.getElementById('btnStop');
  const btnSnap = document.getElementById('btnSnap');
  const camSel  = document.getElementById('camSelect');
  const fpsEl   = document.getElementById('fpsText');
  const flash   = document.getElementById('alertFlash');
  const detList = document.getElementById('detList');
  const detCount= document.getElementById('detCount');

  if (!video) return;

  const ctx     = canvas.getContext('2d');
  let stream    = null;
  let timer     = null;
  let busy      = false;
  const offCtx  = document.createElement('canvas').getContext('2d');
  let fCount    = 0, fTime = Date.now();

  const INTERVAL = 1500;   // ms between detection requests
  const MAX_W    = 640;    // max frame width sent to server
  const QUALITY  = 0.72;   // JPEG quality

  // ─────────────────────────────────────────────────────────────
  btnStart.addEventListener('click', start);
  btnStop .addEventListener('click', stop);
  btnSnap .addEventListener('click', snapshot);

  async function start() {
    const facing = camSel.value;
    const constraints = {
      video: { facingMode: { ideal: facing }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    };

    try {
      stream = await navigator.mediaDevices.getUserMedia(constraints);
      video.srcObject = stream;
      await video.play();
      btnStart.disabled = true;
      btnStop.disabled  = false;
      setStatus('Detecting…', 'text-success');
      timer = setInterval(detectFrame, INTERVAL);
    } catch (e) {
      setStatus('Camera error: ' + e.message, 'text-danger');
    }
  }

  function stop() {
    clearInterval(timer);
    stream?.getTracks().forEach(t => t.stop());
    stream = null;
    video.srcObject = null;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    btnStart.disabled = false;
    btnStop.disabled  = true;
    fpsEl.textContent = '';
    setStatus('Camera stopped — click Start', 'text-muted');
    detList.innerHTML = '<tr><td colspan="4" class="text-muted text-center py-3">Camera stopped</td></tr>';
    detCount.textContent = '0';
  }

  async function detectFrame() {
    if (busy || !video.videoWidth) return;
    busy = true;
    try {
      const b64 = captureFrame();
      const res = await fetch('/api/detect', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ frame: b64, camera_source: 'webcam' }),
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();

      drawBoxes(data.detections || []);
      updateList(data.detections || []);
      if (data.alert_triggered) flashAlert();
      updateFps();
      setStatus(`Detecting… (${data.detection_mode || 'yolo'})`, 'text-success');
    } catch (e) {
      setStatus('Error: ' + e.message, 'text-warning');
    } finally {
      busy = false;
    }
  }

  // Capture one frame as base64 JPEG
  function captureFrame() {
    const vw = video.videoWidth, vh = video.videoHeight;
    const scale = Math.min(1, MAX_W / vw);
    const c = offCtx.canvas;
    c.width  = Math.floor(vw * scale);
    c.height = Math.floor(vh * scale);
    offCtx.drawImage(video, 0, 0, c.width, c.height);
    return c.toDataURL('image/jpeg', QUALITY);
  }

  // Draw bounding boxes + labels on canvas overlay
  function drawBoxes(detections) {
    const rect = video.getBoundingClientRect();
    canvas.width  = rect.width;
    canvas.height = rect.height;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    detections.forEach(det => {
      const bb = det.bounding_box;
      if (!bb) return;

      const x = bb.Left   * canvas.width;
      const y = bb.Top    * canvas.height;
      const w = bb.Width  * canvas.width;
      const h = bb.Height * canvas.height;

      const color = det.color || '#00e676';

      // Box border (thicker red for alerts)
      ctx.strokeStyle = color;
      ctx.lineWidth   = det.is_alert ? 3 : 2;
      ctx.strokeRect(x, y, w, h);

      // Label text
      const labelText = `${det.label} ${det.confidence.toFixed(0)}%`;
      const fontSize  = Math.max(11, canvas.width * 0.017);
      ctx.font        = `bold ${fontSize}px Arial, sans-serif`;
      const tw        = ctx.measureText(labelText).width + 8;
      const th        = fontSize + 7;

      // Label background
      ctx.fillStyle = color;
      ctx.fillRect(x, y - th, tw, th);

      // Label text (dark text on colored background)
      ctx.fillStyle = '#000';
      ctx.fillText(labelText, x + 4, y - 4);

      // Extra alert border glow
      if (det.is_alert) {
        ctx.strokeStyle = 'rgba(255,0,0,0.4)';
        ctx.lineWidth   = 8;
        ctx.strokeRect(x - 3, y - 3, w + 6, h + 6);
      }
    });
  }

  // Update detection list table
  function updateList(detections) {
    detCount.textContent = detections.filter(d => d.bounding_box).length;

    if (!detections.length) {
      detList.innerHTML = '<tr><td colspan="4" class="text-muted text-center">Nothing detected</td></tr>';
      return;
    }

    const typeColors = {
      yolo: '#1d4ed8', label: '#1e40af', face: '#0369a1',
      text: '#15803d', moderation: '#b91c1c', demo: '#78350f',
    };

    detList.innerHTML = detections.map(d => {
      const bg = typeColors[d.detection_type] || '#334155';
      const conf = d.confidence.toFixed(0);
      return `<tr ${d.is_alert ? 'style="background:rgba(239,68,68,.12);"' : ''}>
        <td class="fw-semibold">${d.label}</td>
        <td><span class="badge" style="background:${bg};">${d.detection_type}</span></td>
        <td>
          <div class="d-flex align-items-center gap-1">
            <div style="width:55px;height:5px;background:#1e293b;border-radius:3px;overflow:hidden;">
              <div style="width:${conf}%;height:100%;background:${d.color||'#00e676'};border-radius:3px;"></div>
            </div>
            <small>${conf}%</small>
          </div>
        </td>
        <td>${d.is_alert ? '⚠️' : '—'}</td>
      </tr>`;
    }).join('');
  }

  function flashAlert() {
    flash.classList.remove('d-none', 'pulse-anim');
    void flash.offsetWidth;
    flash.classList.add('pulse-anim');
    setTimeout(() => flash.classList.add('d-none'), 4000);
  }

  function updateFps() {
    fCount++;
    const now = Date.now();
    if (now - fTime >= 3000) {
      fpsEl.textContent = (fCount / ((now - fTime) / 1000)).toFixed(1) + ' fps';
      fCount = 0; fTime = now;
    }
  }

  async function snapshot() {
    if (!video.videoWidth) { alert('Start the camera first.'); return; }
    const b64 = captureFrame();
    try {
      await fetch('/api/snapshot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frame: b64 }),
      });
      toast('Snapshot saved!', 'success');
    } catch (e) {
      toast('Snapshot failed.', 'danger');
    }
  }

  function setStatus(msg, cls) {
    const el = document.getElementById('camStatus');
    el.textContent = msg;
    el.className   = cls || 'text-muted';
  }

  function toast(msg, type = 'info') {
    const t = document.createElement('div');
    t.className = `alert alert-${type} position-fixed bottom-0 end-0 m-3 shadow`;
    t.style.zIndex = 9999;
    t.textContent  = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
  }
})();
