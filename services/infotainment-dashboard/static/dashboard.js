/* SDV Digital Twin Lab — Dashboard WebSocket client */
"use strict";

// ── Constants ──────────────────────────────────────────────────────────────
const MAX_HISTORY = 60;
const RECONNECT_DELAY_MS = 2000;

// ── DOM refs ───────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const badge       = $("connection-badge");
const speedValue  = $("speedValue");
const rpmValue    = $("rpmValue");
const socValue    = $("socValue");
const socBar      = $("socBar");
const highBeamLed = $("highBeamLed");
const highBeamLbl = $("highBeamLabel");
const latValue    = $("latValue");
const lonValue    = $("lonValue");

// ── Chart.js — Speed gauge (doughnut) ─────────────────────────────────────
const gaugeCtx = $("speedGauge").getContext("2d");
const speedGauge = new Chart(gaugeCtx, {
  type: "doughnut",
  data: {
    datasets: [
      {
        data: [0, 250],
        backgroundColor: ["#58a6ff", "#30363d"],
        borderWidth: 0,
        circumference: 270,
        rotation: 225,
      },
    ],
  },
  options: {
    cutout: "78%",
    animation: { duration: 400 },
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
  },
});

function updateGauge(speed) {
  const clamped = Math.min(Math.max(speed, 0), 250);
  speedGauge.data.datasets[0].data = [clamped, 250 - clamped];
  speedGauge.update("none");
}

// ── Chart.js — Speed history sparkline ────────────────────────────────────
const historyCtx = $("speedHistory").getContext("2d");
const historyData = { labels: [], values: [] };
const speedHistory = new Chart(historyCtx, {
  type: "line",
  data: {
    labels: historyData.labels,
    datasets: [
      {
        data: historyData.values,
        borderColor: "#58a6ff",
        backgroundColor: "rgba(88,166,255,0.08)",
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.4,
        fill: true,
      },
    ],
  },
  options: {
    animation: { duration: 200 },
    scales: {
      x: { display: false },
      y: {
        min: 0,
        max: 130,
        grid: { color: "#21262d" },
        ticks: { color: "#8b949e", font: { size: 11 } },
      },
    },
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
  },
});

function pushHistory(speed) {
  const now = new Date().toLocaleTimeString();
  historyData.labels.push(now);
  historyData.values.push(speed);
  if (historyData.labels.length > MAX_HISTORY) {
    historyData.labels.shift();
    historyData.values.shift();
  }
  speedHistory.update("none");
}

// ── Battery SoC colour ─────────────────────────────────────────────────────
function socColor(pct) {
  if (pct > 50) return "#3fb950";   // green
  if (pct > 20) return "#d29922";   // yellow
  return "#f85149";                  // red
}

// ── State update ───────────────────────────────────────────────────────────
function applyState(state) {
  const speed = state["Vehicle.Speed"];
  const rpm   = state["Vehicle.Powertrain.ElectricMotor.Speed"];
  const soc   = state["Vehicle.Powertrain.TractionBattery.StateOfCharge.Current"];
  const beam  = state["Vehicle.Body.Lights.Beam.High.IsOn"];
  const lat   = state["Vehicle.CurrentLocation.Latitude"];
  const lon   = state["Vehicle.CurrentLocation.Longitude"];

  if (speed != null) {
    speedValue.textContent = speed.toFixed(1);
    updateGauge(speed);
    pushHistory(speed);
  }

  if (rpm != null) {
    rpmValue.textContent = rpm.toLocaleString();
  }

  if (soc != null) {
    const pct = Math.round(soc);
    socValue.textContent = pct + " %";
    socBar.style.width = pct + "%";
    socBar.style.background = socColor(pct);
  }

  if (beam != null) {
    const on = beam === true || beam === "true";
    highBeamLed.setAttribute("fill", on ? "#ffe066" : "#333");
    highBeamLed.setAttribute("stroke", on ? "#ffd700" : "#555");
    highBeamLbl.textContent = on ? "ON" : "OFF";
    highBeamLbl.style.color = on ? "#ffe066" : "";
  }

  if (lat != null) latValue.textContent = lat.toFixed(5);
  if (lon != null) lonValue.textContent = lon.toFixed(5);
}

// ── WebSocket connection ───────────────────────────────────────────────────
function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    badge.textContent = "Live";
    badge.className = "badge badge--connected";
  };

  ws.onmessage = (evt) => {
    try {
      applyState(JSON.parse(evt.data));
    } catch (e) {
      console.warn("Bad payload", e);
    }
  };

  ws.onclose = () => {
    badge.textContent = "Disconnected";
    badge.className = "badge badge--disconnected";
    setTimeout(connect, RECONNECT_DELAY_MS);
  };

  ws.onerror = () => ws.close();

  // Keep-alive ping every 20 s
  const ping = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    else clearInterval(ping);
  }, 20_000);
}

connect();
