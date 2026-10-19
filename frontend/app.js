// AgriSense - Frontend Application Logic

let currentLang = 'hi'; // Default to Hindi as per user request
let cropsData = {};
let currentSettings = {};
let latestAdvisory = null;
let telemetryChart = null;
let ws = null;

// ================= INITIALIZATION =================
document.addEventListener('DOMContentLoaded', async () => {
    initChart();
    await loadCrops();
    await loadSettings();
    await fetchLatestTelemetry();
    await fetchHistory();
    await fetchInbox();
    initWebSocket();

    // Periodic backup polling every 5s
    setInterval(fetchLatestTelemetry, 5000);
});

// ================= LANGUAGE TOGGLE =================
const I18N = {
    en: {
        app_title: "AgriSense",
        app_subtitle: "IoT + Cloud Smart Irrigation & Fertilization Advisor",
        lang_btn: "🌐 हिंदी में देखें",
        lbl_crop: "Select Crop",
        lbl_stage: "Growth Stage",
        lbl_field_size: "Field Area (Acres)",
        lbl_farmer_phone: "Farmer WhatsApp / SMS",
        btn_save: "Save & Update Advisor",
        lbl_moist_title: "💧 Soil Moisture",
        lbl_temp_title: "🌡️ Soil Temp & EC",
        lbl_ph_title: "🧪 Soil pH",
        lbl_npk_title: "🌱 Soil NPK (N, P, K)",
        txt_irrig_heading: "💧 Irrigation Advisor",
        txt_fert_heading: "🌱 Fertilization Advisor",
        txt_chart_heading: "📈 Real-Time Sensor Telemetry Trends (24h)"
    },
    hi: {
        app_title: "AgriSense (एग्रीसेंस)",
        app_subtitle: "IoT + क्लाउड स्मार्ट सिंचाई एवं खाद सलाहकार प्रणाली",
        lang_btn: "🌐 View in English",
        lbl_crop: "फसल चुनें",
        lbl_stage: "फसल की विकास अवस्था",
        lbl_field_size: "खेत का क्षेत्रफल (एकड़)",
        lbl_farmer_phone: "किसान का व्हाट्सएप / फोन नंबर",
        btn_save: "सेव करें व सलाह अपडेट करें",
        lbl_moist_title: "💧 मिट्टी में नमी (Moisture)",
        lbl_temp_title: "🌡️ तापमान व चालकता (Temp & EC)",
        lbl_ph_title: "🧪 मिट्टी का पीएच (pH Level)",
        lbl_npk_title: "🌱 मिट्टी में खाद पोषक तत्व (NPK)",
        txt_irrig_heading: "💧 स्मार्ट सिंचाई सलाहकार",
        txt_fert_heading: "🌱 स्मार्ट खाद व पोषण सलाहकार",
        txt_chart_heading: "📈 लाइव सेंसर डेटा एवं रुझान ग्राफ"
    }
};

function toggleLanguage() {
    currentLang = currentLang === 'hi' ? 'en' : 'hi';
    const t = I18N[currentLang];

    document.getElementById('txt-app-title').textContent = t.app_title;
    document.getElementById('txt-app-subtitle').textContent = t.app_subtitle;
    document.getElementById('btn-toggle-lang').textContent = t.lang_btn;
    document.getElementById('lbl-crop').textContent = t.lbl_crop;
    document.getElementById('lbl-stage').textContent = t.lbl_stage;
    document.getElementById('lbl-field-size').textContent = t.lbl_field_size;
    document.getElementById('lbl-farmer-phone').textContent = t.lbl_farmer_phone;
    document.getElementById('btn-save-text').textContent = t.btn_save;
    document.getElementById('lbl-moist-title').textContent = t.lbl_moist_title;
    document.getElementById('lbl-temp-title').textContent = t.lbl_temp_title;
    document.getElementById('lbl-ph-title').textContent = t.lbl_ph_title;
    document.getElementById('lbl-npk-title').textContent = t.lbl_npk_title;
    document.getElementById('txt-irrig-heading').textContent = t.txt_irrig_heading;
    document.getElementById('txt-fert-heading').textContent = t.txt_fert_heading;
    document.getElementById('txt-chart-heading').textContent = t.txt_chart_heading;

    if (latestAdvisory) {
        renderAdvisory(latestAdvisory);
    }
}

// ================= API CALLS =================
async function loadCrops() {
    try {
        const res = await fetch('/api/crops');
        cropsData = await res.json();
    } catch (e) {
        console.error("Failed to load crops:", e);
    }
}

async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        currentSettings = await res.json();
        
        document.getElementById('select-crop').value = currentSettings.active_crop || 'wheat';
        updateStageOptions(currentSettings.active_crop || 'wheat');
        document.getElementById('select-stage').value = currentSettings.active_stage || 'crown_root';
        document.getElementById('input-field-size').value = currentSettings.field_size_acres || 2.5;
        document.getElementById('input-farmer-phone').value = currentSettings.farmer_phone || '+919876543210';
        
        updatePumpUI(currentSettings.pump_override_state, currentSettings.auto_pump_enabled);
    } catch (e) {
        console.error("Failed to load settings:", e);
    }
}

function onCropChange() {
    const selectedCrop = document.getElementById('select-crop').value;
    updateStageOptions(selectedCrop);
}

function updateStageOptions(cropKey) {
    const stageSelect = document.getElementById('select-stage');
    stageSelect.innerHTML = '';
    const crop = cropsData[cropKey];
    if (!crop || !crop.stages) return;

    for (const [key, stage] of Object.entries(crop.stages)) {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = `${stage.name_hi} (${stage.name_en})`;
        stageSelect.appendChild(opt);
    }
}

async function saveSettings() {
    const crop = document.getElementById('select-crop').value;
    const stage = document.getElementById('select-stage').value;
    const fieldSize = parseFloat(document.getElementById('input-field-size').value);
    const phone = document.getElementById('input-farmer-phone').value;

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                active_crop: crop,
                active_stage: stage,
                field_size_acres: fieldSize,
                farmer_phone: phone
            })
        });
        currentSettings = await res.json();
        alert(currentLang === 'hi' ? '✅ सेटिंग्स सफलता से सेव हो गईं!' : '✅ Settings saved successfully!');
        fetchLatestTelemetry();
    } catch (e) {
        alert('Error saving settings: ' + e);
    }
}

// ================= TELEMETRY RENDERING =================
async function fetchLatestTelemetry() {
    try {
        const res = await fetch('/api/telemetry/latest');
        const data = await res.json();
        if (data.telemetry) {
            renderTelemetry(data.telemetry);
        }
        if (data.advisory) {
            latestAdvisory = data.advisory;
            renderAdvisory(data.advisory);
        }
    } catch (e) {
        console.error("Telemetry fetch error:", e);
    }
}

function renderTelemetry(t) {
    // 1. Soil Moisture
    document.getElementById('val-moisture').textContent = t.moisture.toFixed(1);
    const barMoist = document.getElementById('bar-moisture');
    barMoist.style.width = Math.min(100, Math.max(0, t.moisture)) + '%';
    
    const badgeMoist = document.getElementById('badge-moisture');
    if (t.moisture < 25) {
        barMoist.style.background = 'var(--accent-rose)';
        badgeMoist.className = 'badge badge-danger';
        badgeMoist.textContent = currentLang === 'hi' ? 'गंभीर सूखा' : 'Critical Dry';
    } else if (t.moisture < 40) {
        barMoist.style.background = 'var(--accent-amber)';
        badgeMoist.className = 'badge badge-warning';
        badgeMoist.textContent = currentLang === 'hi' ? 'पानी की जरूरत' : 'Needs Water';
    } else if (t.moisture <= 68) {
        barMoist.style.background = 'var(--primary)';
        badgeMoist.className = 'badge badge-success';
        badgeMoist.textContent = currentLang === 'hi' ? 'अनुकूल नमी' : 'Optimal';
    } else {
        barMoist.style.background = 'var(--accent-blue)';
        badgeMoist.className = 'badge badge-info';
        badgeMoist.textContent = currentLang === 'hi' ? 'अत्यधिक नमी / जलभराव' : 'Waterlogged';
    }

    // 2. Temperature & EC
    document.getElementById('val-temperature').textContent = t.temperature.toFixed(1);
    document.getElementById('val-ec').textContent = t.ec ? t.ec.toFixed(0) : '380';

    // 3. pH
    document.getElementById('val-ph').textContent = t.ph.toFixed(1);
    const barPh = document.getElementById('bar-ph');
    const phPct = ((t.ph - 4.0) / (9.0 - 4.0)) * 100;
    barPh.style.width = Math.min(100, Math.max(0, phPct)) + '%';
    
    const badgePh = document.getElementById('badge-ph');
    if (t.ph < 6.0) {
        badgePh.className = 'badge badge-warning';
        badgePh.textContent = currentLang === 'hi' ? 'अम्लीय' : 'Acidic';
    } else if (t.ph > 7.5) {
        badgePh.className = 'badge badge-warning';
        badgePh.textContent = currentLang === 'hi' ? 'क्षारीय' : 'Alkaline';
    } else {
        badgePh.className = 'badge badge-success';
        badgePh.textContent = currentLang === 'hi' ? 'संतुलित' : 'Neutral/Balanced';
    }

    // 4. NPK
    document.getElementById('val-n').textContent = Math.round(t.nitrogen);
    document.getElementById('val-p').textContent = Math.round(t.phosphorus);
    document.getElementById('val-k').textContent = Math.round(t.potassium);

    const targetN = latestAdvisory ? latestAdvisory.n_target : 120;
    const targetP = latestAdvisory ? latestAdvisory.p_target : 50;
    const targetK = latestAdvisory ? latestAdvisory.k_target : 40;

    document.getElementById('target-n').textContent = Math.round(targetN);
    document.getElementById('target-p').textContent = Math.round(targetP);
    document.getElementById('target-k').textContent = Math.round(targetK);

    document.getElementById('bar-n').style.width = Math.min(100, (t.nitrogen / targetN) * 100) + '%';
    document.getElementById('bar-p').style.width = Math.min(100, (t.phosphorus / targetP) * 100) + '%';
    document.getElementById('bar-k').style.width = Math.min(100, (t.potassium / targetK) * 100) + '%';

    // 5. Battery
    document.getElementById('batt-text').textContent = `${t.battery_percentage}% (${t.battery_voltage.toFixed(2)}V)`;

    // 6. Pump UI
    updatePumpUI(t.pump_active, currentSettings.auto_pump_enabled);
}

function renderAdvisory(adv) {
    // Irrigation Box
    const boxIrrig = document.getElementById('box-irrigation');
    const badgeUrgency = document.getElementById('badge-irrig-urgency');
    const titleIrrig = document.getElementById('title-irrig-advice');
    const descIrrig = document.getElementById('desc-irrig-advice');

    if (adv.irrigation_urgency === 'URGENT') {
        boxIrrig.className = 'advice-box urgent';
        badgeUrgency.className = 'badge badge-danger';
        badgeUrgency.textContent = currentLang === 'hi' ? 'अति आवश्यक (URGENT)' : 'URGENT IRRIGATION';
    } else if (adv.irrigation_urgency === 'NORMAL') {
        boxIrrig.className = 'advice-box warning';
        badgeUrgency.className = 'badge badge-warning';
        badgeUrgency.textContent = currentLang === 'hi' ? 'सिंचाई की जरूरत' : 'IRRIGATION RECOMMENDED';
    } else if (adv.irrigation_urgency === 'WATERLOGGED') {
        boxIrrig.className = 'advice-box';
        badgeUrgency.className = 'badge badge-info';
        badgeUrgency.textContent = currentLang === 'hi' ? 'जलभराव' : 'WATERLOGGED';
    } else {
        boxIrrig.className = 'advice-box';
        badgeUrgency.className = 'badge badge-success';
        badgeUrgency.textContent = currentLang === 'hi' ? 'पर्याप्त नमी' : 'OPTIMAL MOISTURE';
    }

    titleIrrig.textContent = currentLang === 'hi' 
        ? `सिंचाई सलाह: ${adv.crop_name_hi} (${adv.stage_name_hi})`
        : `Irrigation Advice: ${adv.crop} (${adv.stage})`;
    descIrrig.textContent = currentLang === 'hi' ? adv.irrigation_advice_hi : adv.irrigation_advice_en;

    // Fertilization Box
    const badgeFert = document.getElementById('badge-fert-status');
    const titleFert = document.getElementById('title-fert-advice');
    const descFert = document.getElementById('desc-fert-advice');
    const dosesContainer = document.getElementById('fert-doses-container');

    if (adv.fertilizer_action_needed) {
        badgeFert.className = 'badge badge-warning';
        badgeFert.textContent = currentLang === 'hi' ? 'खाद की आवश्यकता' : 'FERTILIZER DEFICIT';
    } else {
        badgeFert.className = 'badge badge-success';
        badgeFert.textContent = currentLang === 'hi' ? 'पोषण संतुलित' : 'OPTIMAL NPK';
    }

    titleFert.textContent = currentLang === 'hi' ? 'खेत में खाद एवं पोषण स्थिति' : 'Soil Nutrient & NPK Status';
    descFert.textContent = currentLang === 'hi' ? adv.fertilizer_advice_hi : adv.fertilizer_advice_en;

    dosesContainer.innerHTML = '';
    if (adv.fertilizer_recommendations && adv.fertilizer_recommendations.length > 0) {
        adv.fertilizer_recommendations.forEach(rec => {
            const item = document.createElement('div');
            item.style.background = 'rgba(255,255,255,0.05)';
            item.style.padding = '8px 12px';
            item.style.borderRadius = '6px';
            item.style.fontSize = '0.85rem';
            
            const name = currentLang === 'hi' ? rec.fertilizer_name_hi : rec.fertilizer_name_en;
            item.innerHTML = `<strong>📦 ${name}:</strong> ${rec.dose_per_acre_kg} kg/acre (Total: <strong>${rec.total_field_dose_kg} kg</strong>) • <em>${rec.timing_guidance}</em>`;
            dosesContainer.appendChild(item);
        });
    }

    // pH Box
    const descPh = document.getElementById('desc-ph-advice');
    descPh.textContent = currentLang === 'hi' ? adv.ph_advice_hi : adv.ph_advice_en;
}

function updatePumpUI(isActive, isAuto) {
    const toggle = document.getElementById('pump-toggle');
    const label = document.getElementById('pump-switch-label');
    const sub = document.getElementById('pump-status-sub');

    toggle.checked = isActive;
    if (isActive) {
        label.textContent = currentLang === 'hi' ? 'पंप चालू (ON - सिंचाई जारी)' : 'PUMP ON (WATERING)';
        label.style.color = 'var(--primary)';
    } else {
        label.textContent = currentLang === 'hi' ? 'पंप बंद (OFF)' : 'PUMP OFF';
        label.style.color = 'var(--text-muted)';
    }

    sub.textContent = isAuto 
        ? (currentLang === 'hi' ? 'मोड: स्वचालित ऑटो-सिंचाई सक्रिय' : 'Mode: Auto-Irrigation Enabled')
        : (currentLang === 'hi' ? 'मोड: किसान मैनुअल स्विच' : 'Mode: Manual Override Active');
}

// ================= PUMP TOGGLE =================
async function onPumpToggle(checked) {
    try {
        const res = await fetch('/api/pump/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state: checked })
        });
        const data = await res.json();
        updatePumpUI(data.pump_active, data.auto_pump_enabled);
    } catch (e) {
        console.error("Pump toggle failed:", e);
    }
}

// ================= SCENARIO INJECTION =================
async function triggerScenario(type) {
    let payload = {
        device_id: "AGRI-NODE-001",
        moisture: 45.0,
        temperature: 25.0,
        ph: 6.7,
        nitrogen: 120.0,
        phosphorus: 50.0,
        potassium: 40.0,
        ec: 410.0,
        battery_voltage: 4.1,
        battery_percentage: 92,
        pump_active: false
    };

    if (type === 'drought') {
        payload.moisture = 19.5;
        payload.temperature = 34.0;
    } else if (type === 'low_nitrogen') {
        payload.nitrogen = 35.0;
    } else if (type === 'acidic') {
        payload.ph = 5.2;
    } else if (type === 'rain') {
        payload.moisture = 74.0;
    } else if (type === 'optimal') {
        payload.moisture = 52.0;
        payload.nitrogen = 135.0;
        payload.phosphorus = 48.0;
        payload.potassium = 45.0;
    }

    try {
        const res = await fetch('/api/telemetry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        await fetchLatestTelemetry();
        await fetchHistory();
        await fetchInbox();
    } catch (e) {
        console.error("Scenario trigger error:", e);
    }
}

// ================= TEST ALERT DISPATCH =================
async function triggerTestAlert() {
    try {
        const res = await fetch('/api/alerts/test', { method: 'POST' });
        const data = await res.json();
        await fetchInbox();
        alert(currentLang === 'hi' 
            ? '📲 किसान के फोन पर व्हाट्सएप व एसएमएस अलर्ट भेजा गया!' 
            : '📲 Alert message dispatched to farmer!');
    } catch (e) {
        console.error("Alert trigger error:", e);
    }
}

async function fetchInbox() {
    try {
        const res = await fetch('/api/alerts/inbox');
        const messages = await res.json();
        const chatBody = document.getElementById('phone-chat-body');
        
        if (messages && messages.length > 0) {
            chatBody.innerHTML = '';
            messages.forEach(msg => {
                const bubble = document.createElement('div');
                bubble.className = msg.channel === 'WHATSAPP' ? 'chat-bubble whatsapp' : 'chat-bubble sms';
                bubble.textContent = msg.message;
                
                const timeSpan = document.createElement('span');
                timeSpan.className = 'chat-time';
                timeSpan.textContent = `${msg.channel} • ${msg.timestamp}`;
                bubble.appendChild(timeSpan);

                chatBody.appendChild(bubble);
            });
            chatBody.scrollTop = chatBody.scrollHeight;
        }
    } catch (e) {
        console.error("Inbox fetch error:", e);
    }
}

// ================= CHART.JS =================
function initChart() {
    const ctx = document.getElementById('telemetryChart').getContext('2d');
    telemetryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Soil Moisture (%)',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2.5,
                    yAxisID: 'y'
                },
                {
                    label: 'Soil Temperature (°C)',
                    data: [],
                    borderColor: '#f59e0b',
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    tension: 0.35,
                    borderWidth: 2,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#10b981' },
                    title: { display: true, text: 'Moisture %', color: '#10b981' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    min: 10,
                    max: 45,
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#f59e0b' },
                    title: { display: true, text: 'Temp °C', color: '#f59e0b' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#f8fafc', font: { weight: 'bold' } }
                }
            }
        }
    });
}

async function fetchHistory() {
    try {
        const res = await fetch('/api/telemetry/history?limit=25');
        const records = await res.json();
        if (records && records.length > 0 && telemetryChart) {
            const labels = records.map(r => {
                const dt = new Date(r.timestamp);
                return `${dt.getHours().toString().padStart(2, '0')}:${dt.getMinutes().toString().padStart(2, '0')}:${dt.getSeconds().toString().padStart(2, '0')}`;
            });
            const moistures = records.map(r => r.moisture);
            const temps = records.map(r => r.temperature);

            telemetryChart.data.labels = labels;
            telemetryChart.data.datasets[0].data = moistures;
            telemetryChart.data.datasets[1].data = temps;
            telemetryChart.update();
        }
    } catch (e) {
        console.error("History fetch error:", e);
    }
}

// ================= WEBSOCKET STREAM =================
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/live`;

    try {
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
            console.log("WebSocket connected to AgriSense Live Stream");
            document.getElementById('node-status-text').textContent = 'ESP32 Node-01: LIVE';
        };
        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'TELEMETRY_UPDATE') {
                    renderTelemetry(msg.telemetry);
                    if (msg.advisory) {
                        latestAdvisory = msg.advisory;
                        renderAdvisory(msg.advisory);
                    }
                    fetchHistory();
                    fetchInbox();
                } else if (msg.type === 'PUMP_OVERRIDE') {
                    updatePumpUI(msg.pump_active, msg.auto_pump_enabled);
                }
            } catch (err) {
                console.error("WS parse error:", err);
            }
        };
        ws.onclose = () => {
            console.log("WebSocket closed, retrying in 4s...");
            document.getElementById('node-status-text').textContent = 'ESP32 Node-01: POLLING';
            setTimeout(initWebSocket, 4000);
        };
        ws.onerror = (err) => {
            console.warn("WebSocket error, fallback to HTTP:", err);
            ws.close();
        };
    } catch (e) {
        console.warn("WebSocket initialization failed:", e);
    }
}
