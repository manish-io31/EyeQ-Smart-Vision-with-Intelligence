/**
 * dashboard.js
 *
 * ★ NO-RELOAD REFRESH STRATEGY:
 *   - fetch('/api/stats') every 5 s → update cards + charts + tables in-place.
 *   - The browser NEVER does a full page reload → session cookie is always valid.
 *   - If user hits F5 (browser refresh), Flask re-serves the HTML but the session
 *     cookie is still in the browser → Flask-Login reloads the user automatically
 *     → NO redirect to login page (requires session.permanent = True in auth.py).
 */
(function () {
  'use strict';

  Chart.defaults.color       = '#94a3b8';
  Chart.defaults.borderColor = '#334155';

  let freqChart = null;
  let topChart  = null;

  document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    refresh();
    setInterval(refresh, 5_000);
  });

  async function refresh() {
    try {
      const r = await fetch('/api/stats', { credentials: 'same-origin' });
      if (r.status === 401) { window.location.href = '/auth/login?next=/dashboard'; return; }
      if (!r.ok) return;
      const d = await r.json();

      // Summary cards
      set('totalDetections', d.summary.total_detections);
      set('totalAlerts',     d.summary.total_alerts);
      set('alertsToday',     d.summary.alerts_today);
      set('alertsLastHour',  d.summary.alerts_last_hour);

      // Charts
      if (d.frequency) updateFreq(d.frequency);
      if (d.top_labels) updateTop(d.top_labels);

      // Alerts table
      if (d.recent_alerts) updateAlertsTable(d.recent_alerts);
    } catch (e) {
      console.error('Stats refresh error:', e);
    }
  }

  // ── Charts ───────────────────────────────────────────────────
  function initCharts() {
    const fEl = document.getElementById('freqChart');
    if (fEl) {
      freqChart = new Chart(fEl, {
        type: 'line',
        data: { labels: [], datasets: [{
          label: 'Detections', data: [],
          borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,.1)',
          borderWidth: 2, pointRadius: 3, fill: true, tension: 0.4,
        }]},
        options: {
          responsive: true, maintainAspectRatio: true,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: '#1e293b' }, ticks: { maxTicksLimit: 8 } },
            y: { grid: { color: '#1e293b' }, beginAtZero: true },
          },
        },
      });
    }

    const tEl = document.getElementById('topChart');
    if (tEl) {
      topChart = new Chart(tEl, {
        type: 'doughnut',
        data: { labels: [], datasets: [{
          data: [],
          backgroundColor: ['#ef4444','#f97316','#eab308','#22c55e',
                            '#14b8a6','#3b82f6','#8b5cf6','#ec4899','#06b6d4','#f43f5e'],
          borderWidth: 2, borderColor: '#020617',
        }]},
        options: {
          responsive: true, maintainAspectRatio: true,
          plugins: { legend: { position: 'right', labels: { boxWidth: 10, padding: 8 } } },
          cutout: '55%',
        },
      });
    }
  }

  function updateFreq(frequency) {
    if (!freqChart) return;
    freqChart.data.labels              = frequency.map(f => f.hour);
    freqChart.data.datasets[0].data    = frequency.map(f => f.count);
    freqChart.update('none');
  }

  function updateTop(labels) {
    if (!topChart) return;
    topChart.data.labels            = labels.map(l => l.label);
    topChart.data.datasets[0].data  = labels.map(l => l.count);
    topChart.update('none');
  }

  // ── Recent alerts table ──────────────────────────────────────
  function updateAlertsTable(alerts) {
    const tbody = document.getElementById('alertsBody');
    if (!tbody) return;
    if (!alerts.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-muted text-center py-3">No alerts yet</td></tr>';
      return;
    }
    tbody.innerHTML = alerts.map(a => {
      const conf = a.confidence_score.toFixed(1);
      return `<tr>
        <td class="text-muted">${a.id}</td>
        <td><span class="badge bg-danger">${a.object_detected}</span></td>
        <td>
          <div class="d-flex align-items-center gap-1">
            <div style="width:55px;height:5px;background:#1e293b;border-radius:3px;overflow:hidden;">
              <div style="width:${conf}%;height:100%;background:${a.confidence_score>=80?'#ef4444':'#f59e0b'};"></div>
            </div>
            <small>${conf}%</small>
          </div>
        </td>
        <td class="text-muted small">${a.camera_source}</td>
        <td>${a.sms_sent
              ? '<i class="bi bi-check-circle-fill text-success"></i>'
              : '<i class="bi bi-x-circle text-muted"></i>'}</td>
        <td class="text-muted small">${new Date(a.timestamp).toLocaleString()}</td>
      </tr>`;
    }).join('');
  }

  function set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
  }
})();
