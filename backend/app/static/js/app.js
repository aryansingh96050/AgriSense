// AgriSense Frontend JavaScript Application (Dark Theme Ready)

let ws = null;
let moistureChart = null;
let npkChart = null;

let currentPumpOn = false;
let currentAutoMode = true;
let currentCrop = "Wheat";
let currentFieldArea = 1.0;

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
  cropSelector.addEventListener("change", (e) => {
    updateCrop(e.target.value);
  });

  fieldSizeInput.addEventListener("change", (e) => {
    const val = parseFloat(e.target.value) || 1.0;
    updateFieldArea(val);
  });
});

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
    themeIcon.className = "fa-solid fa-sun text-sm text-amber-400";
  } else {
    localStorage.setItem("agrisense_theme", "light");
    themeIcon.className = "fa-solid fa-moon text-sm text-slate-600";
  }

  // Update chart axes colors on theme switch
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
      currentAutoMode = act.auto_mode;
      currentCrop = act.active_crop || "Wheat";
      currentFieldArea = act.field_area_acres || 1.0;

      cropSelector.value = currentCrop;
      fieldSizeInput.value = currentFieldArea;
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
  currentAutoMode = act.auto_mode;

  if (currentPumpOn) {
    pumpCard.classList.add("pump-active");
    pumpStateBadge.innerText = "RUNNING";
    pumpStateBadge.className = "text-2xl font-black text-sky-400 animate-pulse";
    pumpIconBg.className = "w-8 h-8 rounded-lg bg-sky-500 text-white flex items-center justify-center shadow-lg shadow-sky-500/30";
    pumpOverrideBtn.innerText = "Stop Pump";
    pumpOverrideBtn.className = "px-3 py-1 text-xs font-bold rounded-lg bg-rose-600 hover:bg-rose-500 text-white transition shadow-md shadow-rose-600/30";
  } else {
    pumpCard.classList.remove("pump-active");
    pumpStateBadge.innerText = "OFF";
    pumpStateBadge.className = "text-2xl font-black text-slate-400";
    pumpIconBg.className = "w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 flex items-center justify-center";
    pumpOverrideBtn.innerText = "Start Pump";
    pumpOverrideBtn.className = "px-3 py-1 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-md shadow-emerald-600/30";
  }

  if (currentAutoMode) {
    toggleAutoBtn.innerHTML = '<i class="fa-solid fa-robot mr-1"></i>AUTO';
    toggleAutoBtn.className = "px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800 hover:bg-emerald-900 transition";
  } else {
    toggleAutoBtn.innerHTML = '<i class="fa-solid fa-hand mr-1"></i>MANUAL';
    toggleAutoBtn.className = "px-2.5 py-1 text-xs font-bold rounded-full bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-750 transition";
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

  // Keep max 10 rows
  while (telemetryLogTbody.children.length > 10) {
    telemetryLogTbody.removeChild(telemetryLogTbody.lastChild);
  }
}

// ==================== User Action Triggers ====================
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
    }
  } catch (e) {
    console.error("Error toggling pump:", e);
  }
}

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
    }
  } catch (e) {
    console.error("Error toggling auto mode:", e);
  }
}

async function updateCrop(cropName) {
  try {
    const res = await fetch("/api/v1/actuators/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active_crop: cropName })
    });
    if (res.ok) {
      fetchAdvisories();
    }
  } catch (e) {
    console.error("Error changing crop:", e);
  }
}

async function updateFieldArea(acres) {
  try {
    const res = await fetch("/api/v1/actuators/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field_area_acres: acres })
    });
    if (res.ok) {
      fetchAdvisories();
    }
  } catch (e) {
    console.error("Error updating field area:", e);
  }
}

async function triggerScenario(scenario) {
  try {
    const res = await fetch("/api/v1/telemetry/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: scenario })
    });
    if (res.ok) {
      console.log(`Scenario ${scenario} injected successfully.`);
    }
  } catch (e) {
    console.error("Error triggering scenario:", e);
  }
}
