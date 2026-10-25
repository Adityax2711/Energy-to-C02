/**
 * Energy-to-CO2 Translation Engine Dashboard Logic
 * Handles real-time polling, Chart.js visualizations, region switching,
 * controlled stress-test experiments, and verifiable audit log rendering.
 */

// Global State
let currentRegion = "US-EAST";
let currentPue = 1.20;
let currentSource = "psutil";
let isExperimentPolling = false;
let chartPower = null;
let chartEmissions = null;
let chartRegions = null;
let regionalFactors = [];

// DOM Elements
const selectRegion = document.getElementById("select-region");
const sliderPue = document.getElementById("slider-pue");
const pueValDisplay = document.getElementById("pue-val-display");
const selectSource = document.getElementById("select-source");
const btnRefresh = document.getElementById("btn-refresh");
const btnExportAudit = document.getElementById("btn-export-audit");

// KPI Elements
const valPowerWatts = document.getElementById("val-power-watts");
const valQualityTag = document.getElementById("val-quality-tag");
const powerSourceTag = document.getElementById("power-source-tag");
const valEnergyWh = document.getElementById("val-energy-wh");
const valEnergyKwh = document.getElementById("val-energy-kwh");
const valIntervalsCount = document.getElementById("val-intervals-count");
const valCarbonGrams = document.getElementById("val-carbon-grams");
const valCarbonKg = document.getElementById("val-carbon-kg");
const valEquivalency = document.getElementById("val-equivalency");
const valRegionBadge = document.getElementById("val-region-badge");
const valFactorRegion = document.getElementById("val-factor-region");
const valFactorIntensity = document.getElementById("val-factor-intensity");
const valFactorSource = document.getElementById("val-factor-source");

// Stress Test Elements
const btnStartStress = document.getElementById("btn-start-stress");
const stressDuration = document.getElementById("stress-duration");
const stressProfile = document.getElementById("stress-profile");
const stressTarget = document.getElementById("stress-target");
const stressStatusBadge = document.getElementById("stress-status-badge");
const stressProgressPanel = document.getElementById("stress-progress-panel");
const stressProgressBar = document.getElementById("stress-progress-bar");
const stressLiveStage = document.getElementById("stress-live-stage");
const stressLiveElapsed = document.getElementById("stress-live-elapsed");
const stressLiveTotal = document.getElementById("stress-live-total");
const stressLivePower = document.getElementById("stress-live-power");
const stressLiveLoad = document.getElementById("stress-live-load");
const stressResultsCard = document.getElementById("stress-results-card");
const resBaselineW = document.getElementById("res-baseline-w");
const resPeakW = document.getElementById("res-peak-w");
const resIncreasePct = document.getElementById("res-increase-pct");
const resTotalWh = document.getElementById("res-total-wh");
const resTotalGco2e = document.getElementById("res-total-gco2e");

// Audit Elements
const auditTableBody = document.getElementById("audit-table-body");
const auditCount = document.getElementById("audit-count");

// P1 Forecaster Elements
let chartForecast = null;
let currentForecastHorizon = 24;
const btnRefreshForecast = document.getElementById("btn-refresh-forecast");
const gwTimeRange = document.getElementById("gw-time-range");
const gwTitle = document.getElementById("gw-title");
const gwRecommendation = document.getElementById("gw-recommendation");
const gwSavingsPct = document.getElementById("gw-savings-pct");
const forecastMae = document.getElementById("forecast-mae");
const forecastRmse = document.getElementById("forecast-rmse");
const forecastOptPower = document.getElementById("forecast-opt-power");
const forecastOptCarbon = document.getElementById("forecast-opt-carbon");
const forecastHash = document.getElementById("forecast-hash");

// P2 Anomaly Elements
const valAnomalyScore = document.getElementById("val-anomaly-score");
const anomalyBarFill = document.getElementById("anomaly-bar-fill");
const anomalySeverityBadge = document.getElementById("anomaly-severity-badge");
const anomalyStatusText = document.getElementById("anomaly-status-text");
const anomalyDiagIcon = document.getElementById("anomaly-diag-icon");
const anomalyDiagText = document.getElementById("anomaly-diag-text");
const valAnomalyMean = document.getElementById("val-anomaly-mean");
const valAnomalyStd = document.getElementById("val-anomaly-std");
const valAnomalyGradient = document.getElementById("val-anomaly-gradient");
const valAnomalyZscore = document.getElementById("val-anomaly-zscore");
const btnSimulateSpike = document.getElementById("btn-simulate-spike");
const btnMitigateAnomaly = document.getElementById("btn-mitigate-anomaly");
const inputEvalWatts = document.getElementById("input-eval-watts");
const btnEvalCustom = document.getElementById("btn-eval-custom");

// P3 Right-Sizing Elements
const btnAiRightsizing = document.getElementById("btn-ai-rightsizing");
const rightsizingPanel = document.getElementById("rightsizing-panel");
const awsPeakCpu = document.getElementById("aws-peak-cpu");
const awsPeakCpuVal = document.getElementById("aws-peak-cpu-val");
const rsTitle = document.getElementById("rs-title");
const rsHeadroomBadge = document.getElementById("rs-headroom-badge");
const rsReasoning = document.getElementById("rs-reasoning");
const rsTargetArch = document.getElementById("rs-target-arch");
const rsTargetInst = document.getElementById("rs-target-inst");
const rsPowerSaved = document.getElementById("rs-power-saved");
const rsTargetPower = document.getElementById("rs-target-power");
const rsSameRegionCut = document.getElementById("rs-same-region-cut");
const rsSameRegionKg = document.getElementById("rs-same-region-kg");
const rsComboCut = document.getElementById("rs-combo-cut");
const rsComboKg = document.getElementById("rs-combo-kg");

// P4 Copilot Elements
const copilotInput = document.getElementById("copilot-input");
const btnCopilotSend = document.getElementById("btn-copilot-send");
const copilotResponseCard = document.getElementById("copilot-response-card");
const copilotResponseTitle = document.getElementById("copilot-response-title");
const copilotMarkdownContent = document.getElementById("copilot-markdown-content");
const copilotActionsWrapper = document.getElementById("copilot-actions-wrapper");
const copilotActionsList = document.getElementById("copilot-actions-list");
const btnCopyCopilot = document.getElementById("btn-copy-copilot");

// ==========================================================================
// Chart.js Initialization
// ==========================================================================
function initCharts() {
  const chartPowerCtx = document.getElementById("chart-power").getContext("2d");
  const chartEmissionsCtx = document.getElementById("chart-emissions").getContext("2d");
  const chartRegionsCtx = document.getElementById("chart-regions").getContext("2d");

  // Chart 1: Instantaneous Power Telemetry
  chartPower = new Chart(chartPowerCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label: "Power (Watts)",
        data: [],
        borderColor: "#06B6D4",
        backgroundColor: "rgba(6, 182, 212, 0.12)",
        fill: true,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#64748B", maxTicksLimit: 8, font: { size: 10 } }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94A3B8", font: { size: 10 } },
          title: { display: true, text: "Watts", color: "#64748B", font: { size: 11 } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(14, 22, 38, 0.95)",
          titleColor: "#F8FAFC",
          bodyColor: "#06B6D4",
          borderColor: "rgba(6, 182, 212, 0.3)",
          borderWidth: 1
        }
      }
    }
  });

  // Chart 2: Cumulative Energy and Cumulative Carbon
  chartEmissions = new Chart(chartEmissionsCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Cumulative Energy (Wh)",
          data: [],
          borderColor: "#10B981",
          backgroundColor: "transparent",
          tension: 0.3,
          borderWidth: 2,
          yAxisID: "yEnergy",
          pointRadius: 1
        },
        {
          label: "Cumulative CO2e (Grams)",
          data: [],
          borderColor: "#8B5CF6",
          backgroundColor: "transparent",
          tension: 0.3,
          borderWidth: 2,
          yAxisID: "yCarbon",
          pointRadius: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#64748B", maxTicksLimit: 8, font: { size: 10 } }
        },
        yEnergy: {
          type: "linear",
          position: "left",
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#10B981", font: { size: 10 } },
          title: { display: true, text: "Watt-hours (Wh)", color: "#10B981", font: { size: 11 } }
        },
        yCarbon: {
          type: "linear",
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: { color: "#8B5CF6", font: { size: 10 } },
          title: { display: true, text: "Grams CO2e", color: "#8B5CF6", font: { size: 11 } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(14, 22, 38, 0.95)",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1
        }
      }
    }
  });

  // Chart 3: Regional Grid Comparison Bar Chart
  chartRegions = new Chart(chartRegionsCtx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [{
        label: "Estimated Emissions (gCO2e)",
        data: [],
        backgroundColor: [
          "rgba(6, 182, 212, 0.7)",
          "rgba(16, 185, 129, 0.7)",
          "rgba(245, 158, 11, 0.7)",
          "rgba(59, 130, 246, 0.7)",
          "rgba(239, 68, 68, 0.7)",
          "rgba(139, 92, 246, 0.7)"
        ],
        borderColor: [
          "#06B6D4",
          "#10B981",
          "#F59E0B",
          "#3B82F6",
          "#EF4444",
          "#8B5CF6"
        ],
        borderWidth: 1.5,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#94A3B8", font: { size: 11, weight: "600" } }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#64748B", font: { size: 10 } },
          title: { display: true, text: "Grams CO2e", color: "#64748B", font: { size: 11 } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.parsed.y.toFixed(4)} gCO2e`;
            }
          }
        }
      }
    }
  });

  // Chart 4: P1 AI 24h Forward Predictive Forecaster
  const chartForecastCanvas = document.getElementById("chart-forecast");
  if (chartForecastCanvas) {
    const chartForecastCtx = chartForecastCanvas.getContext("2d");
    chartForecast = new Chart(chartForecastCtx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Predicted Power (W)",
            data: [],
            borderColor: "#38BDF8",
            backgroundColor: "rgba(56, 189, 248, 0.12)",
            borderWidth: 2.5,
            tension: 0.35,
            pointRadius: 2,
            pointHoverRadius: 6,
            yAxisID: "yPower"
          },
          {
            label: "Upper 95% Confidence Interval",
            data: [],
            borderColor: "rgba(56, 189, 248, 0.25)",
            borderDash: [4, 4],
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
            yAxisID: "yPower"
          },
          {
            label: "Lower 95% Confidence Interval",
            data: [],
            borderColor: "rgba(56, 189, 248, 0.25)",
            borderDash: [4, 4],
            borderWidth: 1,
            pointRadius: 0,
            fill: "-1",
            backgroundColor: "rgba(56, 189, 248, 0.08)",
            yAxisID: "yPower"
          },
          {
            label: "Projected Carbon Rate (gCO2e/hr)",
            data: [],
            borderColor: "#A78BFA",
            borderDash: [3, 3],
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.3,
            yAxisID: "yCarbonRate"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        scales: {
          x: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#64748B", maxTicksLimit: 12, font: { size: 10 } }
          },
          yPower: {
            type: "linear",
            position: "left",
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#38BDF8", font: { size: 10 } },
            title: { display: true, text: "Predicted Watts", color: "#38BDF8", font: { size: 11 } }
          },
          yCarbonRate: {
            type: "linear",
            position: "right",
            grid: { drawOnChartArea: false },
            ticks: { color: "#A78BFA", font: { size: 10 } },
            title: { display: true, text: "Rate (gCO2e/hr)", color: "#A78BFA", font: { size: 11 } }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: {
              color: "#94A3B8",
              font: { size: 11 },
              boxWidth: 12
            }
          },
          tooltip: {
            backgroundColor: "rgba(14, 22, 38, 0.95)",
            titleColor: "#F8FAFC",
            borderColor: "rgba(56, 189, 248, 0.3)",
            borderWidth: 1
          }
        }
      }
    });
  }
}

// ==========================================================================
// API Fetch & State Update
// ==========================================================================
async function fetchRegions() {
  try {
    const res = await fetch("/regions");
    if (!res.ok) return;
    regionalFactors = await res.json();
  } catch (err) {
    console.error("Failed to fetch regions:", err);
  }
}

async function updateDashboardData() {
  try {
    // 1. Fetch Energy Summary
    const energyRes = await fetch("/energy/summary");
    if (energyRes.ok) {
      const energyData = await energyRes.json();
      valEnergyWh.textContent = energyData.total_energy_wh.toFixed(3);
      valEnergyKwh.textContent = energyData.total_energy_kwh.toFixed(6);
      valIntervalsCount.textContent = energyData.interval_count;
    }

    // 2. Fetch Carbon Summary for current region and PUE
    const carbonUrl = `/carbon/summary?region=${encodeURIComponent(currentRegion)}&pue=${currentPue}`;
    const carbonRes = await fetch(carbonUrl);
    if (carbonRes.ok) {
      const carbonData = await carbonRes.json();
      valCarbonGrams.textContent = carbonData.total_grams_co2e.toFixed(3);
      valCarbonKg.textContent = carbonData.total_kg_co2e.toFixed(5);
      valRegionBadge.textContent = carbonData.region;
      valFactorRegion.textContent = carbonData.region;
      valFactorIntensity.textContent = carbonData.factor_gco2e_kwh.toFixed(1);
      valFactorSource.textContent = carbonData.factor_source;
      valFactorSource.title = carbonData.factor_source;

      // Real-world equivalency: 1 smartphone charge ≈ 8.22 Wh ≈ ~3.5g CO2e
      const charges = carbonData.total_grams_co2e > 0 ? (carbonData.total_grams_co2e / 3.5).toFixed(1) : "0.0";
      valEquivalency.textContent = `~${charges} smartphone charges`;

      // Update Regional Comparison Chart
      updateRegionalComparisonChart(carbonData.total_energy_kwh);
    }

    // 3. Fetch Timeseries Data for Charts
    const tsUrl = `/carbon/timeseries?region=${encodeURIComponent(currentRegion)}&limit=30`;
    const tsRes = await fetch(tsUrl);
    if (tsRes.ok) {
      const points = await tsRes.json();
      if (points.length > 0) {
        const latestPoint = points[points.length - 1];
        valPowerWatts.textContent = latestPoint.power_w.toFixed(1);

        // Quality badge
        if (latestPoint.quality === "GAP_DETECTED") {
          valQualityTag.className = "quality-badge quality-gap";
          valQualityTag.textContent = "GAP DETECTED";
        } else {
          valQualityTag.className = "quality-badge quality-ok";
          valQualityTag.textContent = "QUALITY: OK";
        }

        // Format chart labels and series
        const labels = points.map(p => {
          const d = new Date(p.timestamp);
          return d.toTimeString().split(" ")[0];
        });
        const powerData = points.map(p => p.power_w);
        const energyData = points.map(p => p.cumulative_energy_wh);
        const carbonData = points.map(p => p.cumulative_grams_co2e);

        // Update Power Chart
        chartPower.data.labels = labels;
        chartPower.data.datasets[0].data = powerData;
        chartPower.update("none");

        // Update Emissions Chart
        chartEmissions.data.labels = labels;
        chartEmissions.data.datasets[0].data = energyData;
        chartEmissions.data.datasets[1].data = carbonData;
        chartEmissions.update("none");
      }
    }

    // 4. Fetch Audit Ledger
    updateAuditLedger();

    // 5. Poll Real-Time Anomaly Status (P2)
    pollLiveAnomalyStatus();

  } catch (err) {
    console.warn("Update poll error:", err);
  }
}

function updateRegionalComparisonChart(totalKwh) {
  if (!chartRegions || regionalFactors.length === 0) return;

  const labels = regionalFactors.map(f => f.region);
  const data = regionalFactors.map(f => {
    // grams = kwh * pue * factor
    return Number((totalKwh * currentPue * f.gco2e_kwh).toFixed(4));
  });

  chartRegions.data.labels = labels;
  chartRegions.data.datasets[0].data = data;
  chartRegions.update("none");
}

async function updateAuditLedger() {
  try {
    const res = await fetch("/audit/ledger?limit=10");
    if (!res.ok) return;
    const ledger = await res.json();
    auditCount.textContent = `${ledger.length} verified events`;

    if (ledger.length === 0) {
      auditTableBody.innerHTML = `<tr><td colspan="6" class="text-center">No audit records yet.</td></tr>`;
      return;
    }

    let rowsHtml = "";
    for (const item of ledger) {
      const d = new Date(item.created_at);
      const timeStr = d.toISOString().replace("T", " ").substring(0, 19);
      const hashStr = item.payload_hash ? `${item.payload_hash.substring(0, 16)}...` : "—";
      
      let detailsPreview = item.details || "";
      if (detailsPreview.length > 70) {
        detailsPreview = detailsPreview.substring(0, 68) + "...";
      }

      rowsHtml += `
        <tr>
          <td class="code-cell">#${item.id}</td>
          <td>${timeStr}</td>
          <td><span class="badge-code">${item.event_type}</span></td>
          <td>${item.host || 'node-alpha-01'}</td>
          <td title="${encodeURIComponent(item.details || '')}">${detailsPreview}</td>
          <td class="hash-cell">${hashStr}</td>
        </tr>
      `;
    }
    auditTableBody.innerHTML = rowsHtml;
  } catch (err) {
    console.error("Audit ledger fetch error:", err);
  }
}

// ==========================================================================
// Controlled Stress-Test Experiment Controller
// ==========================================================================
async function startStressTestExperiment() {
  const duration = parseInt(stressDuration.value, 10);
  const profile = stressProfile.value;
  const targetLoad = parseFloat(stressTarget.value);

  btnStartStress.disabled = true;
  stressStatusBadge.className = "experiment-status-badge running";
  stressStatusBadge.textContent = "EXPERIMENT ACTIVE";
  stressProgressPanel.style.display = "block";
  stressResultsCard.style.display = "none";
  stressLiveTotal.textContent = `${duration}s`;

  try {
    const res = await fetch("/simulate/stress-test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        duration_seconds: duration,
        profile: profile,
        target_load_percent: targetLoad
      })
    });

    if (!res.ok) {
      const err = await res.json();
      alert("Failed to start experiment: " + (err.detail || "Server error"));
      resetStressControls();
      return;
    }

    // Begin polling experiment status
    pollStressExperimentStatus();
  } catch (e) {
    alert("Network error starting experiment: " + e.message);
    resetStressControls();
  }
}

async function pollStressExperimentStatus() {
  try {
    const res = await fetch("/simulate/status");
    if (!res.ok) return;
    const status = await res.json();

    stressProgressBar.style.width = `${status.progress_percent}%`;
    stressLiveElapsed.textContent = `${status.elapsed_seconds.toFixed(1)}s`;
    stressLiveStage.textContent = status.stage;
    stressLivePower.textContent = `${status.current_power_w.toFixed(1)} W`;
    stressLiveLoad.textContent = `${status.current_load_percent.toFixed(1)}%`;

    // Highlight active stage step
    highlightStageStep(status.stage);

    if (status.is_running) {
      setTimeout(pollStressExperimentStatus, 800);
    } else {
      // Completed!
      onStressExperimentComplete(status);
    }
  } catch (e) {
    console.warn("Status poll error:", e);
    setTimeout(pollStressExperimentStatus, 1500);
  }
}

function highlightStageStep(stageName) {
  const steps = [
    document.getElementById("stage-step-1"),
    document.getElementById("stage-step-2"),
    document.getElementById("stage-step-3"),
    document.getElementById("stage-step-4")
  ];
  steps.forEach(s => s.classList.remove("active"));

  if (stageName.includes("BASELINE")) {
    steps[0].classList.add("active");
  } else if (stageName.includes("SPIKE")) {
    steps[1].classList.add("active");
  } else if (stageName.includes("SUSTAINED")) {
    steps[2].classList.add("active");
  } else if (stageName.includes("COOLDOWN")) {
    steps[3].classList.add("active");
  }
}

function onStressExperimentComplete(status) {
  stressStatusBadge.className = "experiment-status-badge completed";
  stressStatusBadge.textContent = "EXPERIMENT COMPLETED";
  btnStartStress.disabled = false;

  if (status.summary) {
    resBaselineW.textContent = `${status.summary.baseline_power_avg_w} W`;
    resPeakW.textContent = `${status.summary.peak_power_avg_w} W`;
    resIncreasePct.textContent = `+${status.summary.power_increase_percent}%`;
    resTotalWh.textContent = `${status.summary.total_energy_wh} Wh`;
    resTotalGco2e.textContent = `${status.summary.total_grams_co2e} gCO₂e`;
    stressResultsCard.style.display = "block";
  }

  // Refresh dashboard data to reflect newly ingested telemetry
  updateDashboardData();
}

function resetStressControls() {
  btnStartStress.disabled = false;
  stressStatusBadge.className = "experiment-status-badge";
  stressStatusBadge.textContent = "STATUS: IDLE";
  stressProgressPanel.style.display = "none";
}

// ==========================================================================
// Event Listeners & Interaction
// ==========================================================================
function setupEventListeners() {
  // Region Selection Change
  selectRegion.addEventListener("change", (e) => {
    currentRegion = e.target.value;
    updateDashboardData();
  });

  // PUE Slider Change
  sliderPue.addEventListener("input", (e) => {
    currentPue = parseFloat(e.target.value);
    pueValDisplay.textContent = currentPue.toFixed(2);
    updateDashboardData();
  });

  // Telemetry Source Mode Change
  selectSource.addEventListener("change", (e) => {
    currentSource = e.target.value;
    powerSourceTag.textContent = currentSource;
  });

  // Refresh Button
  btnRefresh.addEventListener("click", () => {
    updateDashboardData();
  });

  // Export Audit Ledger JSON
  btnExportAudit.addEventListener("click", async () => {
    try {
      const res = await fetch("/audit/ledger?limit=100");
      if (!res.ok) return;
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `energy_co2_provenance_audit_${new Date().toISOString().substring(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to export audit: " + err.message);
    }
  });

  // Start Stress Test Button
  btnStartStress.addEventListener("click", startStressTestExperiment);

  // AWS Event Listeners
  setupAwsEventListeners();

  // AI Suite Event Listeners (P1-P4)
  setupAiEventListeners();
}

// Toast Notification Utility
function showToast(message, type = "success") {
  let container = document.querySelector(".app-toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "app-toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `app-toast ${type === "aws" ? "toast-aws" : ""}`;
  
  const icon = type === "aws" ? "⚡" : type === "error" ? "⚠️" : "✓";
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => {
      if (toast.parentElement) toast.parentElement.removeChild(toast);
    }, 400);
  }, 3500);
}

// ==========================================================================
// AWS Cloud Carbon Optimizer & Region Shifter
// ==========================================================================
const awsSelectInstance = document.getElementById("aws-select-instance");
const awsInstanceCount = document.getElementById("aws-instance-count");
const awsFleetCountVal = document.getElementById("aws-fleet-count-val");
const awsCpuUtil = document.getElementById("aws-cpu-util");
const awsCpuUtilVal = document.getElementById("aws-cpu-util-val");
const awsSourceRegion = document.getElementById("aws-source-region");
const awsTargetRegion = document.getElementById("aws-target-region");
const btnAwsOptimize = document.getElementById("btn-aws-optimize");
const btnAwsInject = document.getElementById("btn-aws-inject");
const awsOutcomePanel = document.getElementById("aws-outcome-panel");

const awsSavingsTitle = document.getElementById("aws-savings-title");
const awsSavingsDesc = document.getElementById("aws-savings-desc");
const awsPctReduction = document.getElementById("aws-pct-reduction");
const awsKpiFleetPower = document.getElementById("aws-kpi-fleet-power");
const awsKpiSinglePower = document.getElementById("aws-kpi-single-power");
const awsKpiMonthlyKwh = document.getElementById("aws-kpi-monthly-kwh");
const awsKpiSourceEmissions = document.getElementById("aws-kpi-source-emissions");
const awsKpiTargetEmissions = document.getElementById("aws-kpi-target-emissions");
const awsKpiSavedKg = document.getElementById("aws-kpi-saved-kg");
const awsKpiAnnualTons = document.getElementById("aws-kpi-annual-tons");
const awsTreesVal = document.getElementById("aws-trees-val");
const awsMilesVal = document.getElementById("aws-miles-val");
const awsPhonesVal = document.getElementById("aws-phones-val");
const awsHashVal = document.getElementById("aws-hash-val");

async function runAwsOptimization(isManualClick = false) {
  if (!awsSelectInstance) return;
  const instanceType = awsSelectInstance.value;
  const count = parseInt(awsInstanceCount.value, 10);
  const cpuPct = parseFloat(awsCpuUtil.value);
  const sourceReg = awsSourceRegion.value;
  const targetReg = awsTargetRegion.value;

  if (isManualClick && btnAwsOptimize) {
    btnAwsOptimize.disabled = true;
    btnAwsOptimize.innerHTML = '<span class="btn-spinner"></span> Calculating Arbitrage...';
    if (awsOutcomePanel) {
      awsOutcomePanel.classList.remove("flash-highlight");
      void awsOutcomePanel.offsetWidth; // trigger reflow
      awsOutcomePanel.classList.add("flash-highlight");
    }
  }

  try {
    const res = await fetch("/aws/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        instance_type: instanceType,
        instance_count: count,
        cpu_utilization_percent: cpuPct,
        hours_per_month: 730.0,
        source_region: sourceReg,
        target_region: targetReg
      })
    });
    
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      showToast("Optimization failed: " + (errData.detail || "Server error"), "error");
      if (btnAwsOptimize) {
        btnAwsOptimize.disabled = false;
        btnAwsOptimize.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> Optimize Carbon';
      }
      return;
    }

    const data = await res.json();

    const isBeneficial = data.optimization_delta.is_beneficial;
    const pct = data.optimization_delta.percent_reduction;
    const savedKg = data.optimization_delta.saved_kg_co2e_monthly;

    if (isBeneficial) {
      awsSavingsTitle.textContent = `Green Shifting Arbitrage: -${pct.toFixed(1)}% Carbon Reduction Available`;
      awsSavingsTitle.style.color = "#34D399";
      awsPctReduction.textContent = `-${pct.toFixed(1)}%`;
      awsPctReduction.style.color = "#10B981";
    } else {
      awsSavingsTitle.textContent = `Region Comparison: +${Math.abs(pct).toFixed(1)}% Emissions Increase`;
      awsSavingsTitle.style.color = "#F43F5E";
      awsPctReduction.textContent = `+${Math.abs(pct).toFixed(1)}%`;
      awsPctReduction.style.color = "#F43F5E";
    }

    awsSavingsDesc.textContent = data.architectural_recommendation;
    awsKpiFleetPower.textContent = `${data.cluster_summary.total_cluster_watts.toFixed(1)} W`;
    awsKpiSinglePower.textContent = `${data.cluster_summary.single_instance_watts.toFixed(1)} W per node (${data.instance_profile.arch})`;
    awsKpiMonthlyKwh.textContent = `${data.cluster_summary.monthly_energy_kwh.toFixed(1)} kWh`;
    awsKpiSourceEmissions.textContent = `${data.source_region_analysis.monthly_kg_co2e.toFixed(1)} kg`;
    awsKpiTargetEmissions.textContent = `${data.target_region_analysis.monthly_kg_co2e.toFixed(1)} kg`;

    awsKpiSavedKg.textContent = `${Math.abs(savedKg).toFixed(1)} kg`;
    awsKpiAnnualTons.textContent = `${data.optimization_delta.saved_metric_tons_co2e_annual.toFixed(2)} Metric Tons/yr`;

    awsTreesVal.textContent = data.real_world_equivalents.mature_trees_planted_offset_months.toFixed(1);
    awsMilesVal.textContent = data.real_world_equivalents.passenger_car_miles_avoided.toLocaleString();
    awsPhonesVal.textContent = data.real_world_equivalents.smartphone_charges_saved.toLocaleString();
    awsHashVal.textContent = data.provenance_hash.substring(0, 16) + "...";

    if (isManualClick && btnAwsOptimize) {
      btnAwsOptimize.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Calculated (-${Math.abs(pct).toFixed(1)}%)`;
      showToast(`✓ AWS Carbon Arbitrage Calculated: -${Math.abs(pct).toFixed(1)}% (${Math.abs(savedKg).toFixed(1)} kg/mo saved)`, "aws");
      setTimeout(() => {
        btnAwsOptimize.disabled = false;
        btnAwsOptimize.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> Optimize Carbon';
      }, 1600);
    }

  } catch (err) {
    console.warn("AWS optimization error:", err);
    showToast("Optimization error: " + err.message, "error");
    if (btnAwsOptimize) {
      btnAwsOptimize.disabled = false;
      btnAwsOptimize.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> Optimize Carbon';
    }
  }
}

async function injectAwsTelemetry() {
  if (!btnAwsInject) return;
  const instanceType = awsSelectInstance.value;
  const count = parseInt(awsInstanceCount.value, 10);
  const cpuPct = parseFloat(awsCpuUtil.value);
  const region = awsSourceRegion.value;

  btnAwsInject.disabled = true;
  btnAwsInject.innerHTML = '<span class="btn-spinner"></span> Streaming...';

  try {
    const res = await fetch("/aws/inject-telemetry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        instance_type: instanceType,
        instance_count: count,
        cpu_utilization_percent: cpuPct,
        region: region
      })
    });
    if (res.ok) {
      btnAwsInject.textContent = "Streamed!";
      showToast(`✓ Streamed ${count}x ${instanceType} (${region}) into Translation Engine!`, "aws");
      await updateDashboardData();
      setTimeout(() => {
        btnAwsInject.disabled = false;
        btnAwsInject.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> Stream to Engine';
      }, 1600);
    } else {
      showToast("Failed to stream telemetry", "error");
      btnAwsInject.disabled = false;
      btnAwsInject.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> Stream to Engine';
    }
  } catch (e) {
    showToast("Network error: " + e.message, "error");
    btnAwsInject.disabled = false;
    btnAwsInject.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> Stream to Engine';
  }
}

function setupAwsEventListeners() {
  if (!awsSelectInstance) return;
  awsInstanceCount.addEventListener("input", (e) => {
    awsFleetCountVal.textContent = `${e.target.value} Nodes`;
    runAwsOptimization(false);
  });
  awsCpuUtil.addEventListener("input", (e) => {
    awsCpuUtilVal.textContent = `${e.target.value}%`;
    runAwsOptimization(false);
  });
  if (awsPeakCpu) {
    awsPeakCpu.addEventListener("input", (e) => {
      if (awsPeakCpuVal) awsPeakCpuVal.textContent = `${e.target.value}%`;
    });
  }
  awsSelectInstance.addEventListener("change", () => runAwsOptimization(false));
  awsSourceRegion.addEventListener("change", () => runAwsOptimization(false));
  awsTargetRegion.addEventListener("change", () => runAwsOptimization(false));
  if (btnAwsOptimize) {
    btnAwsOptimize.addEventListener("click", () => runAwsOptimization(true));
  }
  if (btnAwsInject) {
    btnAwsInject.addEventListener("click", injectAwsTelemetry);
  }
  if (btnAiRightsizing) {
    btnAiRightsizing.addEventListener("click", runAiRightSizing);
  }
}

// ==========================================================================
// P1: AI Predictive Time-Series Forecaster & Green Windows Logic
// ==========================================================================
async function fetchAiForecast(horizonHours = 24) {
  currentForecastHorizon = horizonHours;
  if (btnRefreshForecast) {
    btnRefreshForecast.disabled = true;
    btnRefreshForecast.innerHTML = '<span class="btn-spinner"></span> Forecasting...';
  }

  try {
    const url = `/ai/forecast?horizon_hours=${horizonHours}&region=${encodeURIComponent(currentRegion)}&pue=${currentPue}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Forecast request failed");
    const data = await res.json();

    // 1. Update Green Window Card
    if (data.green_window) {
      const gw = data.green_window;
      const startD = new Date(gw.start_time);
      const endD = new Date(gw.end_time);
      const startStr = startD.toTimeString().split(" ")[0].substring(0, 5);
      const endStr = endD.toTimeString().split(" ")[0].substring(0, 5);

      if (gwTimeRange) gwTimeRange.textContent = `${gw.duration_hours}h Window (${startStr} - ${endStr} UTC)`;
      if (gwTitle) gwTitle.textContent = `Optimal Window: ${gw.optimal_power_w} W (${gw.optimal_carbon_rate_ghr} g/hr)`;
      if (gwRecommendation) gwRecommendation.textContent = gw.recommendation;
      if (gwSavingsPct) gwSavingsPct.textContent = `-${gw.carbon_reduction_percent}%`;
    }

    // 2. Update KPI Chips
    if (forecastMae && data.model_metrics) forecastMae.textContent = `${data.model_metrics.mae_watts.toFixed(2)} W`;
    if (forecastRmse && data.model_metrics) forecastRmse.textContent = `${data.model_metrics.rmse_watts.toFixed(2)} W`;
    if (forecastOptPower && data.green_window) forecastOptPower.textContent = `${data.green_window.optimal_power_w.toFixed(1)} W`;
    if (forecastOptCarbon && data.green_window) forecastOptCarbon.textContent = `${data.green_window.optimal_carbon_rate_ghr.toFixed(1)} g/hr`;
    if (forecastHash && data.provenance) forecastHash.textContent = `${data.provenance.provenance_hash.substring(0, 12)}...`;

    // 3. Update Chart
    if (chartForecast && data.predictions) {
      const labels = data.predictions.map(p => p.hour_label);
      const predPower = data.predictions.map(p => p.predicted_power_w);
      const upperCi = data.predictions.map(p => p.upper_ci_95);
      const lowerCi = data.predictions.map(p => p.lower_ci_95);
      const carbonRate = data.predictions.map(p => p.predicted_carbon_rate_g_per_hr);

      chartForecast.data.labels = labels;
      chartForecast.data.datasets[0].data = predPower;
      chartForecast.data.datasets[1].data = upperCi;
      chartForecast.data.datasets[2].data = lowerCi;
      chartForecast.data.datasets[3].data = carbonRate;
      chartForecast.update();
    }

  } catch (err) {
    console.warn("Forecast fetch error:", err);
  } finally {
    if (btnRefreshForecast) {
      btnRefreshForecast.disabled = false;
      btnRefreshForecast.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Update Forecast';
    }
  }
}

// ==========================================================================
// P2: Full AI Anomaly Detection Pipeline Logic
// ==========================================================================
async function pollLiveAnomalyStatus() {
  try {
    const res = await fetch("/ai/anomalies/live");
    if (!res.ok) return;
    const data = await res.json();

    // 1. Update Gauge & Badges
    const score = Number(data.anomaly_score) || 0;
    if (valAnomalyScore) valAnomalyScore.textContent = score.toFixed(2);
    if (anomalyBarFill) anomalyBarFill.style.width = `${Math.min(100, Math.max(5, score * 100))}%`;

    if (anomalySeverityBadge && anomalyStatusText) {
      anomalyStatusText.textContent = data.status || "NORMAL";
      if (data.status === "CRITICAL_RUNAWAY") {
        anomalySeverityBadge.className = "anomaly-status-badge status-critical";
        if (anomalyDiagIcon) anomalyDiagIcon.textContent = "🚨";
      } else if (data.status === "SUSPICIOUS_SPURT") {
        anomalySeverityBadge.className = "anomaly-status-badge status-suspicious";
        if (anomalyDiagIcon) anomalyDiagIcon.textContent = "⚠️";
      } else {
        anomalySeverityBadge.className = "anomaly-status-badge status-normal";
        if (anomalyDiagIcon) anomalyDiagIcon.textContent = "✓";
      }
    }

    if (anomalyDiagText) anomalyDiagText.textContent = data.diagnostic_message;

    // 2. Rolling Statistics
    if (valAnomalyMean) valAnomalyMean.textContent = `${(data.rolling_mean_w || 0).toFixed(1)} W`;
    if (valAnomalyStd) valAnomalyStd.textContent = `${(data.rolling_std_w || 0).toFixed(1)} W`;
    if (valAnomalyGradient) {
      const grad = data.gradient_w_per_sec || 0;
      valAnomalyGradient.textContent = `${grad > 0 ? '+' : ''}${grad.toFixed(1)} W/s`;
    }
    if (valAnomalyZscore) {
      const z = data.z_score || 0;
      valAnomalyZscore.textContent = `${z > 0 ? '+' : ''}${z.toFixed(2)} σ`;
    }

  } catch (err) {
    console.warn("Anomaly poll error:", err);
  }
}

async function simulateRogueSpike() {
  if (btnSimulateSpike) {
    btnSimulateSpike.disabled = true;
    btnSimulateSpike.innerHTML = '<span class="btn-spinner"></span> Simulating...';
  }

  try {
    // 1. Ingest simulated spike into telemetry stream
    await fetch("/telemetry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        power_w: 185.0,
        source: "psutil",
        host: "alert-test-node"
      })
    });

    // 2. Evaluate anomaly engine
    const evalRes = await fetch("/ai/anomalies/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ power_w: 185.0 })
    });

    if (evalRes.ok) {
      const result = await evalRes.json();
      showToast(`🚨 Rogue CPU Surge Injected: 185W (+${result.z_score}σ)! Anomaly Score: ${result.anomaly_score}`, "aws");
    }

    await pollLiveAnomalyStatus();
    await updateDashboardData();

  } catch (e) {
    showToast("Error simulating surge: " + e.message, "error");
  } finally {
    if (btnSimulateSpike) {
      btnSimulateSpike.disabled = false;
      btnSimulateSpike.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> Simulate Rogue Spike (180W)';
    }
  }
}

async function mitigateWorkload() {
  if (btnMitigateAnomaly) {
    btnMitigateAnomaly.disabled = true;
    btnMitigateAnomaly.innerHTML = '<span class="btn-spinner"></span> Mitigating...';
  }

  try {
    // Ingest baseline idle sample to cooldown the host
    await fetch("/telemetry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        power_w: 34.5,
        source: "psutil",
        host: "alert-test-node"
      })
    });

    await pollLiveAnomalyStatus();
    await updateDashboardData();
    showToast("✓ Workload Mitigated: Dynamic CPU frequency scaling restored baseline power (34.5W).", "success");

  } catch (e) {
    showToast("Mitigation error: " + e.message, "error");
  } finally {
    if (btnMitigateAnomaly) {
      btnMitigateAnomaly.disabled = false;
      btnMitigateAnomaly.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> Mitigate Workload (Cooldown)';
    }
  }
}

async function evaluateCustomWatts() {
  if (!inputEvalWatts) return;
  const watts = parseFloat(inputEvalWatts.value);
  if (isNaN(watts) || watts < 0) {
    showToast("Please enter a valid positive wattage", "error");
    return;
  }

  try {
    const res = await fetch("/ai/anomalies/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ power_w: watts })
    });
    if (res.ok) {
      const data = await res.json();
      showToast(`Evaluated ${watts}W → ${data.status} (Score: ${data.anomaly_score})`, data.is_anomaly ? "aws" : "success");
      await pollLiveAnomalyStatus();
    }
  } catch (e) {
    showToast("Evaluation error: " + e.message, "error");
  }
}

// ==========================================================================
// P3: AI Hardware Right-Sizing Engine Logic
// ==========================================================================
async function runAiRightSizing() {
  if (!btnAiRightsizing) return;
  btnAiRightsizing.disabled = true;
  btnAiRightsizing.innerHTML = '<span class="btn-spinner"></span> Right-Sizing...';

  try {
    const currentInst = awsSelectInstance ? awsSelectInstance.value : "c6i.4xlarge";
    const count = awsInstanceCount ? parseInt(awsInstanceCount.value, 10) : 5;
    const avgCpu = awsCpuUtil ? parseFloat(awsCpuUtil.value) : 25.0;
    const peakCpu = awsPeakCpu ? parseFloat(awsPeakCpu.value) : 45.0;
    const srcReg = awsSourceRegion ? awsSourceRegion.value : "us-east-1";

    const res = await fetch("/ai/rightsizing/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_instance_type: currentInst,
        instance_count: count,
        observed_avg_cpu_percent: avgCpu,
        observed_peak_cpu_percent: peakCpu,
        source_region: srcReg
      })
    });

    if (!res.ok) throw new Error("Right-sizing analysis failed");
    const data = await res.json();

    // Populate Right-Sizing Panel
    if (rightsizingPanel) {
      rightsizingPanel.style.display = "block";
      rightsizingPanel.classList.add("flash-highlight");
      setTimeout(() => rightsizingPanel.classList.remove("flash-highlight"), 700);
    }

    if (rsTitle) rsTitle.textContent = `Workload Architecture Optimization: ${data.workload_profile.current_instance_type} → ${data.recommendation.target_instance_type}`;
    if (rsHeadroomBadge) rsHeadroomBadge.textContent = `${data.workload_profile.wasted_headroom_percent}% Headroom Trimmed`;
    if (rsReasoning) rsReasoning.textContent = data.recommendation.reasoning;
    if (rsTargetArch) rsTargetArch.textContent = `${data.recommendation.target_arch}`;
    if (rsTargetInst) rsTargetInst.textContent = data.recommendation.target_instance_type;
    if (rsPowerSaved) rsPowerSaved.textContent = `-${data.same_region_savings.power_reduction_watts} W`;
    if (rsTargetPower) rsTargetPower.textContent = `${data.recommendation.recommended_fleet_power_w} W target draw`;
    if (rsSameRegionCut) rsSameRegionCut.textContent = `-${data.same_region_savings.percent_carbon_reduction}%`;
    if (rsSameRegionKg) rsSameRegionKg.textContent = `${data.same_region_savings.monthly_kg_co2e_saved} kg CO₂e/mo saved`;
    if (rsComboCut) rsComboCut.textContent = `-${data.combined_with_green_region.combined_percent_reduction}%`;
    if (rsComboKg) rsComboKg.textContent = `${data.combined_with_green_region.combined_monthly_kg_co2e_saved} kg CO₂e/mo saved`;

    showToast(`✓ AI Right-Sizing Calculated: -${data.same_region_savings.percent_carbon_reduction}% (${data.same_region_savings.monthly_kg_co2e_saved} kg/mo saved)`, "aws");

  } catch (err) {
    showToast("Right-sizing error: " + err.message, "error");
  } finally {
    if (btnAiRightsizing) {
      btnAiRightsizing.disabled = false;
      btnAiRightsizing.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg> P3: AI Right-Size';
    }
  }
}

// ==========================================================================
// P4: AI Sustainability Copilot Logic
// ==========================================================================
function renderMarkdownToHtml(mdText) {
  let html = mdText
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/`([^`]+)`/gim, '<code>$1</code>')
    .replace(/^\- (.*$)/gim, '<li>$1</li>');

  // Wrap consecutive list items in <ul>
  html = html.replace(/(<li>.*<\/li>(\s*<li>.*<\/li>)*)/gim, '<ul>$1</ul>');
  // Paragraphs
  html = html.replace(/\n\n/gim, '<br/><br/>');
  return html;
}

async function sendCopilotQuery(promptText) {
  if (!promptText || promptText.trim().length === 0) return;
  if (btnCopilotSend) {
    btnCopilotSend.disabled = true;
    btnCopilotSend.innerHTML = '<span class="btn-spinner"></span> Analyzing...';
  }

  try {
    const res = await fetch("/ai/copilot/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: promptText,
        region: currentRegion,
        pue: currentPue
      })
    });

    if (!res.ok) throw new Error("Copilot API request failed");
    const data = await res.json();

    if (copilotResponseCard) {
      copilotResponseCard.style.display = "block";
      copilotResponseCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    if (copilotResponseTitle) copilotResponseTitle.textContent = data.title || "Sustainability Copilot Analysis";
    if (copilotMarkdownContent) copilotMarkdownContent.innerHTML = renderMarkdownToHtml(data.response_markdown || "");

    // Suggested actions checklist
    if (data.suggested_actions && data.suggested_actions.length > 0) {
      if (copilotActionsWrapper) copilotActionsWrapper.style.display = "block";
      if (copilotActionsList) {
        copilotActionsList.innerHTML = data.suggested_actions.map(act => `<li>${act}</li>`).join("");
      }
    } else {
      if (copilotActionsWrapper) copilotActionsWrapper.style.display = "none";
    }

    // Set raw markdown for copying
    if (btnCopyCopilot) {
      btnCopyCopilot.onclick = () => {
        navigator.clipboard.writeText(data.response_markdown);
        showToast("✓ Copilot response copied to clipboard!", "success");
      };
    }

  } catch (err) {
    showToast("Copilot error: " + err.message, "error");
  } finally {
    if (btnCopilotSend) {
      btnCopilotSend.disabled = false;
      btnCopilotSend.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Ask Copilot';
    }
  }
}

function setupAiEventListeners() {
  // P1 Horizon Toggles & Refresh
  document.querySelectorAll("#forecast-horizon-group .btn-toggle").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll("#forecast-horizon-group .btn-toggle").forEach(b => b.classList.remove("active"));
      e.target.classList.add("active");
      const h = parseInt(e.target.getAttribute("data-horizon"), 10);
      fetchAiForecast(h);
    });
  });
  if (btnRefreshForecast) {
    btnRefreshForecast.addEventListener("click", () => fetchAiForecast(currentForecastHorizon));
  }

  // P2 Anomaly Actions
  if (btnSimulateSpike) {
    btnSimulateSpike.addEventListener("click", simulateRogueSpike);
  }
  if (btnMitigateAnomaly) {
    btnMitigateAnomaly.addEventListener("click", mitigateWorkload);
  }
  if (btnEvalCustom) {
    btnEvalCustom.addEventListener("click", evaluateCustomWatts);
  }
  if (inputEvalWatts) {
    inputEvalWatts.addEventListener("keydown", (e) => {
      if (e.key === "Enter") evaluateCustomWatts();
    });
  }

  // P4 Copilot Actions
  if (btnCopilotSend && copilotInput) {
    btnCopilotSend.addEventListener("click", () => {
      sendCopilotQuery(copilotInput.value);
    });
    copilotInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        sendCopilotQuery(copilotInput.value);
      }
    });
  }
  document.querySelectorAll(".copilot-pill").forEach(pill => {
    pill.addEventListener("click", (e) => {
      const q = e.target.getAttribute("data-prompt");
      if (copilotInput) copilotInput.value = q;
      sendCopilotQuery(q);
    });
  });

  // Feature Navigation Pills
  document.querySelectorAll(".feature-nav-bar .nav-pill").forEach(pill => {
    pill.addEventListener("click", (e) => {
      document.querySelectorAll(".feature-nav-bar .nav-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
    });
  });
}

// Global window exposure for inline HTML onclick handlers
window.runAwsOptimization = runAwsOptimization;
window.injectAwsTelemetry = injectAwsTelemetry;
window.showToast = showToast;
window.runAiRightSizing = runAiRightSizing;
window.fetchAiForecast = fetchAiForecast;
window.simulateRogueSpike = simulateRogueSpike;
window.mitigateWorkload = mitigateWorkload;
window.sendCopilotQuery = sendCopilotQuery;

// ==========================================================================
// App Initialization
// ==========================================================================
document.addEventListener("DOMContentLoaded", async () => {
  initCharts();
  setupEventListeners();
  await fetchRegions();
  await updateDashboardData();
  await runAwsOptimization(false);
  await fetchAiForecast(24);
  await pollLiveAnomalyStatus();

  // Periodic poll every 2 seconds
  setInterval(updateDashboardData, 2000);
});


