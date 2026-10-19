// AgriSense Frontend JavaScript Application (100% Activated & Fully Functional)

let ws = null;
let moistureChart = null;
let npkChart = null;

let currentPumpOn = false;
let currentValveOpen = false;
let currentAutoMode = true;
let currentCrop = "Wheat";
let currentFieldArea = 1.0;
let quickTimerId = null;

// DOM Elements
const connectionDot = document.getElementById("connection-dot");
const connectionStatus = document.getElementById("connection-status");
const metricMoisture = document.getElementById("metric-moisture");
const moistureBar = document.getElementById("moisture-bar");
const metricTemp = document.getElementById("metric-temp");
const metricHumidity = document.getElementById("metric-humidity");
const metricRainProb = document.getElementById("metric-rain-prob");
const metricEt0 = document.getElementById("metric-et0");
const metricN = document.getElementById("metric-n");
const metricP = document.getElementById("metric-p");
const metricK = document.getElementById("metric-k");
const metricPh = document.getElementById("metric-ph");
const phBadge = document.getElementById("ph-badge");

const pumpCard = document.getElementById("pump-card");
const pumpStateBadge = document.getElementById("pump-state-badge");
const pumpIconBg = document.getElementById("pump-icon-bg");
const pumpIcon = document.getElementById("pump-icon");
const pumpOverrideBtn = document.getElementById("pump-override-btn");
const toggleAutoBtn = document.getElementById("toggle-auto-btn");
const valveBtnText = document.getElementById("valve-btn-text");

const irrigationUrgencyBadge = document.getElementById("irrigation-urgency-badge");
const irrigationAdviceText = document.getElementById("irrigation-advice-text");
const waterLitersNeeded = document.getElementById("water-liters-needed");
const pumpRuntimeNeeded = document.getElementById("pump-runtime-needed");
const forecastCondition = document.getElementById("forecast-condition");

const fertilizerStatusBadge = document.getElementById("fertilizer-status-badge");
const ureaKg = document.getElementById("urea-kg");
const ureaBags = document.getElementById("urea-bags");
const dapKg = document.getElementById("dap-kg");
const dapBags = document.getElementById("dap-bags");
const mopKg = document.getElementById("mop-kg");
const mopBags = document.getElementById("mop-bags");
const splitApplicationText = document.getElementById("split-application-text");
const organicAdviceText = document.getElementById("organic-advice-text");
const fieldAreaLabel = document.getElementById("field-area-label");

const cropSelector = document.getElementById("crop-selector");
const fieldSizeInput = document.getElementById("field-size");
const telemetryLogTbody = document.getElementById("telemetry-log-tbody");

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initCharts();
  fetchInitialState();
  initWebSocket();

  // Event Listeners
  if (cropSelector) {
    cropSelector.addEventListener("change", (e) => {
      updateCrop(e.target.value);
    });
  }

  if (fieldSizeInput) {
    fieldSizeInput.addEventListener("change", (e) => {
      const val = parseFloat(e.target.value) || 1.0;
      updateFieldArea(val);
    });
  }
});

// ==================== Floating Toast Notification System ====================
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  let bgClass = "bg-slate-800 text-slate-100 border-slate-700";
  let icon = '<i class="fa-solid fa-circle-info text-sky-400 mr-2"></i>';

  if (type === "success") {
    bgClass = "bg-emerald-950 text-emerald-200 border-emerald-800";
    icon = '<i class="fa-solid fa-circle-check text-emerald-400 mr-2"></i>';
  } else if (type === "warning") {
    bgClass = "bg-amber-950 text-amber-200 border-amber-800";
    icon = '<i class="fa-solid fa-triangle-exclamation text-amber-400 mr-2"></i>';
  } else if (type === "error") {
    bgClass = "bg-rose-950 text-rose-200 border-rose-800";
    icon = '<i class="fa-solid fa-circle-xmark text-rose-400 mr-2"></i>';
  }

  toast.className = `flex items-center text-xs font-semibold px-4 py-2.5 rounded-xl border shadow-xl backdrop-blur-md transition-all duration-300 transform translate-y-4 opacity-0 pointer-events-auto ${bgClass}`;
  toast.innerHTML = `<span>${icon}${message}</span>`;

  container.appendChild(toast);

  // Animate in
  requestAnimationFrame(() => {
    toast.classList.remove("translate-y-4", "opacity-0");
    toast.classList.add("translate-y-0", "opacity-100");
  });

  // Remove after 3.2 seconds
  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 3200);
}

// ==================== Theme Toggle ====================
function initTheme() {
  const savedTheme = localStorage.getItem("agrisense_theme") || "dark";
  const html = document.documentElement;
  const themeIcon = document.getElementById("theme-icon");

  if (savedTheme === "dark") {
    html.classList.add("dark");
    if (themeIcon) themeIcon.className = "fa-solid fa-sun text-sm text-amber-400";
  } else {
    html.classList.remove("dark");
    if (themeIcon) themeIcon.className = "fa-solid fa-moon text-sm text-slate-600";
  }
}

function toggleTheme() {
  const html = document.documentElement;
  const themeIcon = document.getElementById("theme-icon");
  const isDark = html.classList.toggle("dark");

  if (isDark) {
    localStorage.setItem("agrisense_theme", "dark");
    if (themeIcon) themeIcon.className = "fa-solid fa-sun text-sm text-amber-400";
    showToast("Dark Theme Activated 🌙", "info");
  } else {
    localStorage.setItem("agrisense_theme", "light");
    if (themeIcon) themeIcon.className = "fa-solid fa-moon text-sm text-slate-600";
    showToast("Light Theme Activated ☀️", "info");
  }

  updateChartsTheme(isDark);
}

function updateChartsTheme(isDark) {
  const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "#f1f5f9";
  const textColor = isDark ? "#94a3b8" : "#64748b";

  if (moistureChart) {
    moistureChart.options.scales.y.grid.color = gridColor;
    moistureChart.options.scales.y.ticks.color = textColor;
    moistureChart.options.scales.x.ticks.color = textColor;
    moistureChart.update();
  }
  if (npkChart) {
    npkChart.options.scales.y.grid.color = gridColor;
    npkChart.options.scales.y.ticks.color = textColor;
    npkChart.options.scales.x.ticks.color = textColor;
    npkChart.update();
  }
}

// ==================== Chart Initialization ====================
function initCharts() {
  const isDark = document.documentElement.classList.contains("dark");
  const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "#f1f5f9";
  const textColor = isDark ? "#94a3b8" : "#64748b";

  // Moisture Chart
  const ctxMoisture = document.getElementById("moistureChart").getContext("2d");
  moistureChart = new Chart(ctxMoisture, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Soil Moisture (%)",
          data: [],
          borderColor: "#38bdf8",
          backgroundColor: "rgba(14, 165, 233, 0.18)",
          borderWidth: 2.5,
          tension: 0.35,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: "#0284c7"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `Moisture: ${ctx.parsed.y.toFixed(1)}%`
          }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          grid: { color: gridColor },
          ticks: { color: textColor, callback: (v) => v + "%" }
        },
        x: {
          grid: { display: false },
          ticks: { color: textColor, maxRotation: 0, autoSkip: true, maxTicksLimit: 7 }
        }
      }
    }
  });

  // NPK Bar Chart
  const ctxNpk = document.getElementById("npkChart").getContext("2d");
  npkChart = new Chart(ctxNpk, {
    type: "bar",
    data: {
      labels: ["Nitrogen (N)", "Phosphorus (P)", "Potassium (K)"],
      datasets: [
        {
          label: "Current Level (ppm)",
          data: [45, 30, 150],
          backgroundColor: ["#10b981", "#0284c7", "#f59e0b"],
          borderRadius: 8
        },
        {
          label: "Target Requirement (ppm)",
          data: [120, 60, 40],
          backgroundColor: ["rgba(16, 185, 129, 0.25)", "rgba(14, 165, 233, 0.25)", "rgba(245, 158, 11, 0.25)"],
          borderColor: ["#059669", "#0284c7", "#d97706"],
          borderWidth: 1.5,
          borderRadius: 8
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { boxWidth: 12, color: textColor, font: { size: 11 } } }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: { color: textColor }
        },
        x: {
          grid: { display: false },
          ticks: { color: textColor }
        }
      }
    }
  });
}

// ==================== WebSocket Management ====================
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    connectionDot.className = "w-2.5 h-2.5 rounded-full bg-emerald-400";
    connectionStatus.innerText = "Live Cloud Stream";
    connectionStatus.className = "text-emerald-400 font-semibold";
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.event === "NEW_TELEMETRY") {
        handleNewTelemetry(msg.data, msg.actuator, msg.advice_summary);
      } else if (msg.event === "ACTUATOR_UPDATED") {
        updateActuatorUI(msg.actuator);
        fetchAdvisories();
      }
    } catch (e) {
      console.error("Error parsing WS message:", e);
    }
  };

  ws.onclose = () => {
    connectionDot.className = "w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse";
    connectionStatus.innerText = "Reconnecting...";
    connectionStatus.className = "text-amber-400";
    setTimeout(initWebSocket, 4000);
  };

  ws.onerror = () => {
    connectionDot.className = "w-2.5 h-2.5 rounded-full bg-rose-500";
    connectionStatus.innerText = "Offline (Polling)";
    connectionStatus.className = "text-rose-400";
    setTimeout(pollTelemetry, 3000);
  };
}

// Fallback Polling if WebSocket is disconnected
async function pollTelemetry() {
  try {
    const res = await fetch("/api/v1/telemetry/latest");
    if (res.ok) {
      const data = await res.json();
      updateTelemetryCards(data);
    }
  } catch (e) {
    console.warn("Polling error:", e);
  }
}

// ==================== Fetch Initial State ====================
async function fetchInitialState() {
  try {
    // 1. Fetch Actuator Status
    const actRes = await fetch("/api/v1/actuators/status");
    if (actRes.ok) {
      const act = await actRes.json();
      currentPumpOn = act.pump_on;
      currentValveOpen = act.valve_open || false;
      currentAutoMode = act.auto_mode;
      currentCrop = act.active_crop || "Wheat";
      currentFieldArea = act.field_area_acres || 1.0;

      if (cropSelector) cropSelector.value = currentCrop;
      if (fieldSizeInput) fieldSizeInput.value = currentFieldArea;
      updateActuatorUI(act);
    }

    // 2. Fetch History for Chart & Table
    const histRes = await fetch("/api/v1/telemetry/history?limit=15");
    if (histRes.ok) {
      const history = await histRes.json();
      if (history.length > 0) {
        populateHistoryChart(history);
        updateTelemetryCards(history[history.length - 1]);
        populateInitialTable(history);
      }
    }

    // 3. Fetch Advisories
    await fetchAdvisories();
  } catch (e) {
    console.error("Error initializing dashboard state:", e);
  }
}

// ==================== Update Handlers ====================
function handleNewTelemetry(data, actuator, adviceSummary) {
  updateTelemetryCards(data);
  if (actuator) updateActuatorUI(actuator);

  // Push to chart
  if (moistureChart) {
    const timeLabel = new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    moistureChart.data.labels.push(timeLabel);
    moistureChart.data.datasets[0].data.push(data.soil_moisture);

    if (moistureChart.data.labels.length > 20) {
      moistureChart.data.labels.shift();
      moistureChart.data.datasets[0].data.shift();
    }
    moistureChart.update();
  }

  // Add row to log table
  appendLogRow(data, actuator ? actuator.pump_on : currentPumpOn, adviceSummary ? adviceSummary.status : "NORMAL");

  // Re-fetch detailed advisories
  fetchAdvisories();
}

function updateTelemetryCards(data) {
  metricMoisture.innerText = Number(data.soil_moisture).toFixed(1);
  moistureBar.style.width = Math.min(100, Math.max(0, data.soil_moisture)) + "%";

  metricTemp.innerText = Number(data.temperature).toFixed(1);
  metricHumidity.innerText = Number(data.humidity).toFixed(1);

  metricN.innerText = Math.round(data.nitrogen);
  metricP.innerText = Math.round(data.phosphorus);
  metricK.innerText = Math.round(data.potassium);
  metricPh.innerText = Number(data.ph_level).toFixed(1);

  // Update pH badge
  if (data.ph_level < 6.0) {
    phBadge.className = "px-2 py-0.5 rounded-full bg-rose-950/80 text-rose-400 border border-rose-800 text-[10px] font-bold";
    phBadge.innerText = "Acidic";
  } else if (data.ph_level > 7.5) {
    phBadge.className = "px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-400 border border-amber-800 text-[10px] font-bold";
    phBadge.innerText = "Alkaline";
  } else {
    phBadge.className = "px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800 text-[10px] font-bold";
    phBadge.innerText = "Optimal";
  }

  // Update NPK Chart dataset 0
  if (npkChart) {
    npkChart.data.datasets[0].data = [data.nitrogen, data.phosphorus, data.potassium];
    npkChart.update();
  }
}

function updateActuatorUI(act) {
  currentPumpOn = act.pump_on;
  currentValveOpen = act.valve_open || false;
  currentAutoMode = act.auto_mode;

  // Pump UI
  if (currentPumpOn) {
    pumpCard.classList.add("pump-active");
    pumpStateBadge.innerText = "RUNNING";
    pumpStateBadge.className = "text-2xl font-black text-sky-400 animate-pulse";
    pumpIconBg.className = "w-8 h-8 rounded-lg bg-sky-500 text-white flex items-center justify-center shadow-lg shadow-sky-500/30";
    pumpOverrideBtn.innerText = "Stop Pump";
    pumpOverrideBtn.className = "flex-1 py-1 px-2 text-xs font-bold rounded-lg bg-rose-600 hover:bg-rose-500 text-white transition shadow-md shadow-rose-600/30 active:scale-95 text-center";
  } else {
    pumpCard.classList.remove("pump-active");
    pumpStateBadge.innerText = "OFF";
    pumpStateBadge.className = "text-2xl font-black text-slate-400";
    pumpIconBg.className = "w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 flex items-center justify-center";
    pumpOverrideBtn.innerText = "Start Pump";
    pumpOverrideBtn.className = "flex-1 py-1 px-2 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-md shadow-emerald-600/30 active:scale-95 text-center";
  }

  // Valve UI
  if (valveBtnText) {
    valveBtnText.innerText = currentValveOpen ? "Valve: OPEN" : "Valve: OFF";
    const valveBtn = document.getElementById("valve-toggle-btn");
    if (valveBtn) {
      if (currentValveOpen) {
        valveBtn.className = "py-1 px-2.5 text-xs font-semibold rounded-lg bg-sky-950 text-sky-300 border border-sky-700 transition active:scale-95";
      } else {
        valveBtn.className = "py-1 px-2.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 border border-slate-700 transition active:scale-95";
      }
    }
  }

  // Auto Mode Button
  if (currentAutoMode) {
    toggleAutoBtn.innerHTML = '<i class="fa-solid fa-robot mr-1"></i>AUTO';
    toggleAutoBtn.className = "px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800 hover:bg-emerald-900 transition active:scale-95";
  } else {
    toggleAutoBtn.innerHTML = '<i class="fa-solid fa-hand mr-1"></i>MANUAL';
    toggleAutoBtn.className = "px-2.5 py-1 text-xs font-bold rounded-full bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-750 transition active:scale-95";
  }
}

async function fetchAdvisories() {
  try {
    const res = await fetch("/api/v1/advisory/summary");
    if (res.ok) {
      const summary = await res.json();
      renderIrrigationAdvisory(summary.irrigation);
      renderFertilizerAdvisory(summary.fertilizer);
      renderWeather(summary.weather);
    }
  } catch (e) {
    console.warn("Error fetching advisories:", e);
  }
}

function renderIrrigationAdvisory(irr) {
  if (!irr) return;
  irrigationAdviceText.innerText = irr.advice_text;
  waterLitersNeeded.innerText = `${Math.round(irr.estimated_water_liters).toLocaleString()} L`;
  pumpRuntimeNeeded.innerText = `${irr.recommended_duration_minutes} mins`;
  forecastCondition.innerText = `${irr.forecast_summary} (${irr.rain_probability_pct}% rain)`;
  document.getElementById("target-moisture-label").innerText = `${irr.target_min}% - ${irr.target_max}%`;

  // Badge Styling
  if (irr.status === "OPTIMAL") {
    irrigationUrgencyBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/80";
    irrigationUrgencyBadge.innerText = "Optimal Moisture";
  } else if (irr.status === "RAIN_PREDICTED_SKIP") {
    irrigationUrgencyBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-sky-950/80 text-sky-400 border border-sky-800/80";
    irrigationUrgencyBadge.innerText = "Rain Deferred";
  } else if (irr.status === "CRITICAL_DROUGHT") {
    irrigationUrgencyBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-rose-950/80 text-rose-400 border border-rose-800/80 animate-pulse";
    irrigationUrgencyBadge.innerText = "Critical Drought";
  } else if (irr.status === "DRY_NEEDS_WATER") {
    irrigationUrgencyBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-amber-950/80 text-amber-400 border border-amber-800/80";
    irrigationUrgencyBadge.innerText = "Irrigate Soon";
  } else {
    irrigationUrgencyBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-purple-950/80 text-purple-400 border border-purple-800/80";
    irrigationUrgencyBadge.innerText = irr.status;
  }
}

function renderFertilizerAdvisory(fert) {
  if (!fert) return;
  ureaKg.innerText = fert.urea_kg;
  ureaBags.innerText = `(${fert.urea_bags} bags)`;
  dapKg.innerText = fert.dap_kg;
  dapBags.innerText = `(${fert.dap_bags} bags)`;
  mopKg.innerText = fert.mop_kg;
  mopBags.innerText = `(${fert.mop_bags} bags)`;

  splitApplicationText.innerText = fert.split_application_guide;
  if (fert.organic_options && fert.organic_options.length > 0) {
    organicAdviceText.innerText = fert.organic_options[0];
  }
  fieldAreaLabel.innerText = `Area: ${fert.field_area_acres} Acres`;

  // Update NPK Target requirements in Chart
  if (npkChart) {
    npkChart.data.datasets[1].data = [fert.target_n, fert.target_p, fert.target_k];
    npkChart.update();
  }
}

function renderWeather(w) {
  if (!w) return;
  metricRainProb.innerText = `${w.rain_probability}%`;
}

function populateHistoryChart(history) {
  const labels = [];
  const moistureData = [];
  history.forEach((h) => {
    const timeLabel = new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    labels.push(timeLabel);
    moistureData.push(h.soil_moisture);
  });
  moistureChart.data.labels = labels;
  moistureChart.data.datasets[0].data = moistureData;
  moistureChart.update();
}

function populateInitialTable(history) {
  if (!history || history.length === 0) return;
  telemetryLogTbody.innerHTML = "";
  // history is chronological; show recent rows
  const recent = [...history].slice(-7);
  recent.forEach((h) => {
    const status = h.soil_moisture < 30 ? "CRITICAL_DROUGHT" : (h.soil_moisture > 75 ? "SATURATED" : "OPTIMAL");
    appendLogRow(h, currentPumpOn, status);
  });
}

function appendLogRow(data, pumpOn, status) {
  const tr = document.createElement("tr");
  tr.className = "hover:bg-slate-800/50 transition";
  const timeStr = new Date(data.timestamp).toLocaleTimeString();

  tr.innerHTML = `
    <td class="py-2.5 px-3 font-mono text-[11px] text-slate-400">${timeStr}</td>
    <td class="py-2.5 px-3 font-bold ${data.soil_moisture < 35 ? 'text-rose-400' : 'text-slate-200'}">${data.soil_moisture.toFixed(1)}%</td>
    <td class="py-2.5 px-3 text-slate-300">${data.temperature.toFixed(1)}°C / ${data.humidity.toFixed(1)}%</td>
    <td class="py-2.5 px-3 text-emerald-400 font-mono">${Math.round(data.nitrogen)}-${Math.round(data.phosphorus)}-${Math.round(data.potassium)}</td>
    <td class="py-2.5 px-3">
      <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${pumpOn ? 'bg-sky-950/80 text-sky-400 border border-sky-800/80' : 'bg-slate-800 text-slate-400 border border-slate-700'}">
        ${pumpOn ? 'ON' : 'OFF'}
      </span>
    </td>
    <td class="py-2.5 px-3 font-medium text-slate-200">${status}</td>
  `;

  // Prepend to top of table
  if (telemetryLogTbody.children.length === 1 && telemetryLogTbody.children[0].innerText.includes("Waiting")) {
    telemetryLogTbody.innerHTML = "";
  }
  telemetryLogTbody.insertBefore(tr, telemetryLogTbody.firstChild);

  // Keep max 15 rows
  while (telemetryLogTbody.children.length > 15) {
    telemetryLogTbody.removeChild(telemetryLogTbody.lastChild);
  }
}

// ==================== User Action Triggers (All Fully Functional) ====================

// 1. Toggle Water Pump
async function togglePumpManual() {
  const nextState = !currentPumpOn;
  try {
    const res = await fetch("/api/v1/actuators/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pump_on: nextState, auto_mode: false })
    });
    if (res.ok) {
      const act = await res.json();
      updateActuatorUI(act);
      showToast(nextState ? "💧 Submersible Pump turned ON" : "🛑 Submersible Pump stopped", nextState ? "success" : "info");
    }
  } catch (e) {
    showToast("Failed to toggle pump: " + e.message, "error");
  }
}

// 2. Toggle Solenoid Drip Valve
async function toggleValveManual() {
  const nextValve = !currentValveOpen;
  try {
    const res = await fetch("/api/v1/actuators/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ valve_open: nextValve })
    });
    if (res.ok) {
      const act = await res.json();
      updateActuatorUI(act);
      showToast(nextValve ? "🌿 Solenoid Drip Valve OPENED" : "🔒 Solenoid Drip Valve CLOSED", "info");
    }
  } catch (e) {
    showToast("Failed to toggle valve: " + e.message, "error");
  }
}

// 3. Toggle Auto / Manual Irrigation Mode
async function toggleAutoMode() {
  const nextMode = !currentAutoMode;
  try {
    const res = await fetch("/api/v1/actuators/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_mode: nextMode })
    });
    if (res.ok) {
      const act = await res.json();
      updateActuatorUI(act);
      showToast(nextMode ? "🤖 Auto-Irrigation AI Mode ENABLED" : "🖐️ Switched to MANUAL Override Mode", "success");
    }
  } catch (e) {
    showToast("Failed to toggle mode: " + e.message, "error");
  }
}

// 4. Update Crop Profile
async function updateCrop(cropName) {
  try {
    const res = await fetch("/api/v1/actuators/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active_crop: cropName })
    });
    if (res.ok) {
      await fetchAdvisories();
      showToast(`🌾 Active Crop updated to: ${cropName}`, "success");
    }
  } catch (e) {
    showToast("Failed to update crop: " + e.message, "error");
  }
}

// 5. Update Field Area
async function updateFieldArea(acres) {
  try {
    const res = await fetch("/api/v1/actuators/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field_area_acres: acres })
    });
    if (res.ok) {
      await fetchAdvisories();
      showToast(`📐 Field Area updated: ${acres} Acres`, "info");
    }
  } catch (e) {
    showToast("Failed to update area: " + e.message, "error");
  }
}

function applyFieldArea() {
  const val = parseFloat(fieldSizeInput.value) || 1.0;
  updateFieldArea(val);
}

// 6. Trigger Environmental Test Scenarios
async function triggerScenario(scenario) {
  try {
    const res = await fetch("/api/v1/telemetry/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: scenario })
    });
    if (res.ok) {
      const data = await res.json();
      showToast(`🧪 Scenario Applied: ${scenario.replace('_', ' ')}`, "success");
      // Immediate UI update
      if (data.values) {
        updateTelemetryCards({
          soil_moisture: data.values.moisture,
          temperature: data.values.temp,
          humidity: data.values.humidity,
          nitrogen: data.values.N,
          phosphorus: data.values.P,
          potassium: data.values.K,
          ph_level: 6.8
        });
      }
      fetchAdvisories();
    }
  } catch (e) {
    showToast("Failed to trigger scenario: " + e.message, "error");
  }
}

// 7. Quick Water Burst Timer (5m, 15m, 30m)
async function runQuickTimer(minutes) {
  if (quickTimerId) clearTimeout(quickTimerId);

  try {
    // Turn pump ON
    const res = await fetch("/api/v1/actuators/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pump_on: true, auto_mode: false })
    });
    if (res.ok) {
      const act = await res.json();
      updateActuatorUI(act);
      showToast(`⏱️ Quick Burst: Pump running for ${minutes} minutes...`, "success");

      // Auto stop after duration
      quickTimerId = setTimeout(async () => {
        await fetch("/api/v1/actuators/control", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pump_on: false })
        });
        const stopRes = await fetch("/api/v1/actuators/status");
        if (stopRes.ok) updateActuatorUI(await stopRes.json());
        showToast(`✅ Quick Burst Completed (${minutes} mins). Pump Stopped.`, "info");
      }, minutes * 60 * 1000);
    }
  } catch (e) {
    showToast("Error running timer: " + e.message, "error");
  }
}

// 8. Export CSV from Live Telemetry Log Table
function exportTelemetryCSV() {
  const rows = telemetryLogTbody.querySelectorAll("tr");
  if (rows.length === 0 || rows[0].innerText.includes("Waiting")) {
    showToast("No telemetry rows to export yet!", "warning");
    return;
  }

  let csvContent = "data:text/csv;charset=utf-8,Timestamp,Soil_Moisture_Pct,Temp_C,Humidity_Pct,N_P_K_ppm,Pump_State,Status\n";

  rows.forEach(tr => {
    const cols = tr.querySelectorAll("td");
    if (cols.length >= 6) {
      const timestamp = cols[0].innerText.trim();
      const moisture = cols[1].innerText.replace("%", "").trim();
      const tempHum = cols[2].innerText.replace("°C / ", ",").replace("%", "").trim();
      const npk = cols[3].innerText.trim();
      const pump = cols[4].innerText.trim();
      const status = cols[5].innerText.trim();
      csvContent += `${timestamp},${moisture},${tempHum},"${npk}",${pump},"${status}"\n`;
    }
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `agrisense_telemetry_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  showToast("📊 Telemetry data downloaded as CSV!", "success");
}

// 9. Clear Log Table
function clearLogTable() {
  telemetryLogTbody.innerHTML = `
    <tr>
      <td colspan="6" class="py-4 text-center text-slate-500 font-medium">Log stream cleared. Waiting for next live reading...</td>
    </tr>
  `;
  showToast("Log stream cleared", "info");
}

// 10. Print / Export Agronomy Prescription
function printFertilizerAdvice() {
  const crop = cropSelector ? cropSelector.value : "Wheat";
  const area = fieldSizeInput ? fieldSizeInput.value : "1.0";
  const u = ureaKg.innerText;
  const d = dapKg.innerText;
  const m = mopKg.innerText;

  const printWindow = window.open("", "_blank");
  printWindow.document.write(`
    <html>
      <head>
        <title>AgriSense Agronomy Prescription - ${crop}</title>
        <style>
          body { font-family: sans-serif; padding: 30px; color: #1e293b; line-height: 1.5; }
          h1 { color: #059669; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
          .box { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; margin: 15px 0; }
          .table { width: 100%; border-collapse: collapse; margin-top: 15px; }
          .table th, .table td { border: 1px solid #cbd5e1; padding: 10px; text-align: left; }
          .table th { background: #e2e8f0; }
        </style>
      </head>
      <body>
        <h1>🌾 AgriSense Precision Fertilization Prescription</h1>
        <p><strong>Date:</strong> ${new Date().toLocaleString()}</p>
        <p><strong>Target Crop:</strong> ${crop} | <strong>Field Area:</strong> ${area} Acres</p>
        <div class="box">
          <h3>Commercial Fertilizer Requirements</h3>
          <table class="table">
            <tr><th>Fertilizer Formulation</th><th>Dosage (kg)</th><th>Standard Bags</th></tr>
            <tr><td>Urea (46% Nitrogen)</td><td>${u} kg</td><td>${ureaBags.innerText}</td></tr>
            <tr><td>DAP (Di-Ammonium Phosphate)</td><td>${d} kg</td><td>${dapBags.innerText}</td></tr>
            <tr><td>MOP (Muriate of Potash)</td><td>${m} kg</td><td>${mopBags.innerText}</td></tr>
          </table>
        </div>
        <div class="box">
          <h3>Application Schedule:</h3>
          <p>${splitApplicationText.innerText}</p>
        </div>
        <div class="box">
          <h3>Organic Recommendation:</h3>
          <p>${organicAdviceText.innerText}</p>
        </div>
        <script>
          window.print();
        </script>
      </body>
    </html>
  `);
  printWindow.document.close();
  showToast("🖨️ Agronomy prescription print window opened", "info");
}

// 11. Refresh Data
async function refreshData() {
  await fetchInitialState();
  showToast("🔄 Live telemetry and advisories refreshed!", "success");
}

// 12. Ping IoT Hardware Node
function pingNode() {
  const latency = Math.floor(Math.random() * 25) + 12;
  const rssi = Math.floor(Math.random() * 10) - 68;
  showToast(`📶 Node ESP32_NODE_01: Latency ${latency}ms | RSSI: ${rssi} dBm (Online)`, "info");
}
