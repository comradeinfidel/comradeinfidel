'use strict';

// ------------------------------------------------------------------ //
// State                                                               //
// ------------------------------------------------------------------ //
let isRunning = false;
let pnlChart = null;
let eventSource = null;

// ------------------------------------------------------------------ //
// DOM helpers                                                         //
// ------------------------------------------------------------------ //
const $ = (sel) => document.querySelector(sel);
const fmt = (n, digits = 2) =>
  n == null ? '—' : Number(n).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
const fmtPct = (n) => n == null ? '—' : `${(Number(n) * 100).toFixed(1)}%`;
const fmtTime = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('en-US', { hour12: false });
};

// ------------------------------------------------------------------ //
// SSE / Agent Log                                                     //
// ------------------------------------------------------------------ //
function connectSSE() {
  if (eventSource) { eventSource.close(); }
  const log = $('#agent-log');
  const dot = $('.dot');

  eventSource = new EventSource('/api/agent/stream');

  eventSource.onopen = () => {
    dot.classList.add('live');
  };

  eventSource.onmessage = (e) => {
    try {
      const entry = JSON.parse(e.data);
      appendLogEntry(log, entry);
    } catch (_) {}
  };

  eventSource.onerror = () => {
    dot.classList.remove('live');
    // Reconnect after 5s
    setTimeout(connectSSE, 5000);
  };
}

function appendLogEntry(log, entry) {
  if (entry.type === 'ping') return;

  const div = document.createElement('div');
  div.className = `log-entry ${entry.type || 'info'}`;

  const ts = document.createElement('span');
  ts.className = 'ts';
  ts.textContent = entry.timestamp ? entry.timestamp.slice(11, 19) : '';

  const msg = document.createElement('span');
  msg.className = 'msg';
  msg.textContent = entry.message || '';

  div.appendChild(ts);
  div.appendChild(msg);
  log.appendChild(div);

  // Auto-scroll to bottom
  log.scrollTop = log.scrollHeight;

  // Keep log from growing forever in the DOM (keep last 500 entries)
  while (log.children.length > 500) {
    log.removeChild(log.firstChild);
  }
}

// ------------------------------------------------------------------ //
// Agent controls                                                      //
// ------------------------------------------------------------------ //
async function startAgent() {
  const btn = $('#btn-toggle');
  btn.disabled = true;
  try {
    const r = await fetch('/api/agent/start', { method: 'POST' });
    if (!r.ok) {
      const err = await r.json();
      alert('Failed to start: ' + (err.detail || JSON.stringify(err)));
      return;
    }
    setRunning(true);
  } finally {
    btn.disabled = false;
  }
}

async function stopAgent() {
  const btn = $('#btn-toggle');
  btn.disabled = true;
  try {
    const r = await fetch('/api/agent/stop', { method: 'POST' });
    if (!r.ok) {
      const err = await r.json();
      alert('Failed to stop: ' + (err.detail || JSON.stringify(err)));
      return;
    }
    setRunning(false);
  } finally {
    btn.disabled = false;
  }
}

function setRunning(running) {
  isRunning = running;
  const badge = $('#status-badge');
  const btn = $('#btn-toggle');
  badge.textContent = running ? '● RUNNING' : '○ STOPPED';
  badge.className = 'status-badge ' + (running ? 'running' : 'stopped');
  btn.textContent = running ? 'Stop Agent' : 'Start Agent';
  btn.className = running ? 'danger' : 'primary';
  btn.onclick = running ? stopAgent : startAgent;
}

$('#btn-toggle').onclick = startAgent;

// ------------------------------------------------------------------ //
// Status polling                                                      //
// ------------------------------------------------------------------ //
async function pollStatus() {
  try {
    const r = await fetch('/api/status');
    if (!r.ok) return;
    const data = await r.json();
    setRunning(data.running);

    const todayPnl = data.today_pnl ?? 0;
    const totalPnl = data.total_realized_pnl ?? 0;

    const todayEl = $('#stat-today-pnl');
    todayEl.textContent = '$' + fmt(todayPnl);
    todayEl.className = todayPnl >= 0 ? 'pos' : 'neg';

    const totalEl = $('#stat-total-pnl');
    totalEl.textContent = '$' + fmt(totalPnl);
    totalEl.className = totalPnl >= 0 ? 'pos' : 'neg';

    if (data.next_run) {
      $('#stat-next-run').textContent = fmtTime(data.next_run);
    }
  } catch (_) {}
}

// ------------------------------------------------------------------ //
// Balance                                                             //
// ------------------------------------------------------------------ //
async function refreshBalance() {
  try {
    const r = await fetch('/api/balance');
    if (!r.ok) return;
    const data = await r.json();
    const balance = data.usdc_balance ?? data.balance ?? '—';
    $('#balance-pm').textContent = '$' + fmt(balance);
  } catch (_) {}
}

// ------------------------------------------------------------------ //
// Positions table                                                     //
// ------------------------------------------------------------------ //
async function refreshPositions() {
  try {
    const r = await fetch('/api/positions');
    if (!r.ok) return;
    const data = await r.json();
    const positions = data.positions || [];
    renderPositions(positions);
  } catch (_) {}
}

function renderPositions(positions) {
  const tbody = $('#positions-tbody');
  tbody.innerHTML = '';

  const valid = positions.filter(p => !p.error);
  if (valid.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="no-data">No open positions</td></tr>';
    return;
  }

  for (const p of valid) {
    const upnl = p.unrealized_pnl ?? 0;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${(p.outcome || '—').toUpperCase()}</td>
      <td>${fmtPct(p.avg_price)}</td>
      <td>${fmtPct(p.current_price)}</td>
      <td>${fmt(p.size)}</td>
      <td class="${upnl >= 0 ? 'pnl-pos' : 'pnl-neg'}">$${fmt(upnl)}</td>
    `;
    tbody.appendChild(tr);
  }
}

// ------------------------------------------------------------------ //
// PnL chart                                                           //
// ------------------------------------------------------------------ //
async function refreshPnlChart() {
  try {
    const r = await fetch('/api/pnl');
    if (!r.ok) return;
    const data = await r.json();
    const history = data.daily_history || [];
    renderChart(history);
  } catch (_) {}
}

function renderChart(history) {
  const labels = history.map(d => d.date);
  const values = history.map(d => d.pnl);

  const ctx = $('#pnl-chart').getContext('2d');

  if (pnlChart) {
    pnlChart.data.labels = labels;
    pnlChart.data.datasets[0].data = values;
    pnlChart.update('none');
    return;
  }

  pnlChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Daily PnL ($)',
        data: values,
        borderColor: '#00e5a0',
        backgroundColor: 'rgba(0,229,160,0.08)',
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#00e5a0',
        fill: true,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `$${fmt(ctx.parsed.y)}`,
          },
          backgroundColor: '#1e1e1e',
          borderColor: '#2a2a2a',
          borderWidth: 1,
          titleColor: '#666',
          bodyColor: '#e8e8e8',
        },
      },
      scales: {
        x: {
          ticks: { color: '#666', font: { size: 10 } },
          grid: { color: '#1a1a1a' },
        },
        y: {
          ticks: {
            color: '#666',
            font: { size: 10 },
            callback: v => '$' + fmt(v),
          },
          grid: { color: '#1a1a1a' },
        },
      },
    },
  });
}

// ------------------------------------------------------------------ //
// Config panel                                                        //
// ------------------------------------------------------------------ //
async function loadConfig() {
  try {
    const r = await fetch('/api/config');
    if (!r.ok) return;
    const cfg = await r.json();
    $('#cfg-max-pos').value = cfg.max_position_size_usd;
    $('#cfg-loss-limit').value = cfg.daily_loss_limit_usd;
    $('#cfg-max-open').value = cfg.max_open_positions;
    $('#cfg-max-orders').value = cfg.max_orders_per_cycle;
    $('#cfg-interval').value = cfg.agent_interval_minutes;
  } catch (_) {}
}

async function saveConfig() {
  const body = {
    max_position_size_usd: Number($('#cfg-max-pos').value) || undefined,
    daily_loss_limit_usd: Number($('#cfg-loss-limit').value) || undefined,
    max_open_positions: Number($('#cfg-max-open').value) || undefined,
    max_orders_per_cycle: Number($('#cfg-max-orders').value) || undefined,
    agent_interval_minutes: Number($('#cfg-interval').value) || undefined,
  };
  try {
    const r = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (r.ok) {
      const el = $('#cfg-save-msg');
      el.textContent = 'Saved!';
      setTimeout(() => { el.textContent = ''; }, 2000);
    }
  } catch (_) {}
}

$('#btn-save-cfg').onclick = saveConfig;

// ------------------------------------------------------------------ //
// Boot                                                                //
// ------------------------------------------------------------------ //
(async function init() {
  connectSSE();
  await pollStatus();
  await Promise.all([refreshBalance(), refreshPositions(), refreshPnlChart(), loadConfig()]);

  // Polling intervals
  setInterval(pollStatus, 10_000);
  setInterval(refreshBalance, 60_000);
  setInterval(refreshPositions, 30_000);
  setInterval(refreshPnlChart, 60_000);
})();
