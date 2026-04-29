const form = document.getElementById("simulationForm");
const backendUrlInput = document.getElementById("backendUrl");
const backendStatus = document.getElementById("backendStatus");
const backendUrlLabel = document.getElementById("backendUrlLabel");
const runStatusBadge = document.getElementById("runStatusBadge");
const runStartedAt = document.getElementById("runStartedAt");
const runFinishedAt = document.getElementById("runFinishedAt");
const configPreview = document.getElementById("configPreview");
const messageBox = document.getElementById("messageBox");
const alertsTableBody = document.getElementById("alertsTableBody");
const runButton = document.getElementById("runButton");
const refreshButton = document.getElementById("refreshButton");
const replayCanvas = document.getElementById("replayCanvas");
const replayStep = document.getElementById("replayStep");
const replayVehicleCount = document.getElementById("replayVehicleCount");
const playReplayButton = document.getElementById("playReplayButton");
const pauseReplayButton = document.getElementById("pauseReplayButton");
const replaySpeedHalfButton = document.getElementById("replaySpeedHalfButton");
const replaySpeedNormalButton = document.getElementById("replaySpeedNormalButton");
const replaySpeedDoubleButton = document.getElementById("replaySpeedDoubleButton");
const backToTopButton = document.getElementById("backToTopButton");
const replayContext = replayCanvas.getContext("2d");

let replayData = null;
let replayIndex = 0;
let replayTimer = null;
let replayRunId = null;
let replayFrameCount = 0;
let latestRunStatus = "idle";
let liveReplayPoller = null;
let replaySpeed = 1;

const istDateTimeFormatter = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: true,
});

function getBackendUrl() {
  return backendUrlInput.value.trim().replace(/\/+$/, "");
}

function setMessage(text, type = "info") {
  messageBox.textContent = text;
  messageBox.className = "message-box";
  if (type === "error") {
    messageBox.classList.add("failed");
  }
}

function updateBackToTopVisibility() {
  if (window.scrollY > 320) {
    backToTopButton.classList.add("visible");
  } else {
    backToTopButton.classList.remove("visible");
  }
}

function resetUiState() {
  stopReplay();
  stopLiveReplayPolling();
  replayData = null;
  replayIndex = 0;
  replayRunId = null;
  replayFrameCount = 0;
  latestRunStatus = "idle";
  replaySpeed = 1;
  backendUrlLabel.textContent = getBackendUrl();
  backendStatus.textContent = "Not checked";
  runStatusBadge.textContent = "Idle";
  runStatusBadge.className = "badge ok";
  runStartedAt.textContent = "Not started";
  runFinishedAt.textContent = "Not finished";
  configPreview.textContent = "No run yet.";
  playReplayButton.disabled = false;
  updateReplaySpeedButtons();
  setMessage("Ready.");
  drawReplayFrame();
  refreshRows();
}

function updateReplaySpeedButtons() {
  replaySpeedHalfButton.classList.toggle("active", replaySpeed === 0.5);
  replaySpeedNormalButton.classList.toggle("active", replaySpeed === 1);
  replaySpeedDoubleButton.classList.toggle("active", replaySpeed === 2);
}

function setReplaySpeed(nextSpeed) {
  replaySpeed = nextSpeed;
  updateReplaySpeedButtons();
  if (replayTimer) {
    startReplay({ restartIfComplete: false });
  }
}

function setRunStatus(status) {
  latestRunStatus = status || "Unknown";
  runStatusBadge.textContent = status || "Unknown";
  runStatusBadge.className = "badge";
  if (status === "running") runStatusBadge.classList.add("running");
  if (status === "completed") runStatusBadge.classList.add("completed");
  if (status === "failed") runStatusBadge.classList.add("failed");
  if (status === "idle") runStatusBadge.classList.add("ok");
  playReplayButton.disabled = status === "running";
}

function formatIstTimestamp(timestamp) {
  if (!timestamp) {
    return "";
  }

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }

  return `${istDateTimeFormatter.format(date)} IST`;
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${getBackendUrl()}${path}`, options);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return response.json();
}

function renderTimelineRows(trace) {
  const rows = [];

  if (trace && trace.frames) {
    trace.frames.forEach((frame) => {
      frame.vehicles.forEach((vehicle) => {
        const roadLength = trace.meta?.road_length_m ?? 1200;
        rows.push({
          step: frame.step,
          vehicle_id: vehicle.vehicle_id,
          status: vehicle.status ?? "",
          edge_id: vehicle.edge_id ?? "",
          x: vehicle.x ?? "",
          speed_kmph: vehicle.speed_kmph ?? "",
          limit_kmph: vehicle.limit_kmph ?? "",
          distance_left_m:
            typeof vehicle.x === "number" ? Math.max(0, roadLength - vehicle.x).toFixed(2) : "",
          y: vehicle.y ?? "",
        });
      });
    });
  }

  if (rows.length === 0) {
    alertsTableBody.innerHTML = `
      <tr>
        <td colspan="9" class="empty-state">No simulation timeline loaded yet.</td>
      </tr>
    `;
    return;
  }

  alertsTableBody.innerHTML = rows
    .map((row) => `
      <tr>
        <td>${row.step ?? ""}</td>
        <td>${row.vehicle_id ?? ""}</td>
        <td>${row.status ?? ""}</td>
        <td>${row.edge_id ?? ""}</td>
        <td>${row.x ?? ""}</td>
        <td>${row.speed_kmph ?? ""}</td>
        <td>${row.limit_kmph ?? ""}</td>
        <td>${row.distance_left_m ?? ""}</td>
        <td>${row.y ?? ""}</td>
      </tr>
    `)
    .join("");
}

function statusColor(status) {
  if (status === "danger") return "#ff7a21";
  if (status === "speeding") return "#e74c3c";
  if (status === "warned") return "#f1c40f";
  return "#2ecc71";
}

function edgeColor(edgeId) {
  if (edgeId === "e0") return "rgba(81, 120, 186, 0.18)";
  if (edgeId === "e1") return "rgba(255, 214, 10, 0.28)";
  return "rgba(72, 201, 176, 0.22)";
}

function drawReplayFrame() {
  if (!replayData || !replayData.frames || replayData.frames.length === 0) {
    replayContext.clearRect(0, 0, replayCanvas.width, replayCanvas.height);
    replayContext.fillStyle = "#6b7280";
    replayContext.font = '16px "Instrument Sans", sans-serif';
    replayContext.fillText("No replay data loaded yet.", 20, 40);
    replayStep.textContent = "Step --";
    replayVehicleCount.textContent = "Vehicles --";
    return;
  }

  const width = replayCanvas.width;
  const height = replayCanvas.height;
  const roadLeft = 40;
  const roadRight = width - 40;
  const roadY = 126;
  const roadHeight = 26;
  const roadLength = replayData.meta?.road_length_m ?? 1200;
  const pxPerMeter = (roadRight - roadLeft) / roadLength;
  const frame = replayData.frames[replayIndex] || replayData.frames[0];

  replayContext.clearRect(0, 0, width, height);

  replayData.road_segments.forEach((segment) => {
    const x = roadLeft + segment.start_m * pxPerMeter;
    const w = (segment.end_m - segment.start_m) * pxPerMeter;
    replayContext.fillStyle = edgeColor(segment.edge_id);
    replayContext.fillRect(x, roadY - 20, w, roadHeight + 40);
    replayContext.fillStyle = "#374151";
    replayContext.font = '15px "Space Grotesk", sans-serif';
    replayContext.fillText(
      `${segment.edge_id.toUpperCase()} • ${segment.limit_kmph} km/h`,
      x + 8,
      roadY - 28
    );
  });

  replayContext.fillStyle = "#2f3640";
  replayContext.fillRect(roadLeft, roadY, roadRight - roadLeft, roadHeight);

  replayData.rsus.forEach((rsu) => {
    const cx = roadLeft + rsu.x * pxPerMeter;
    replayContext.fillStyle = "rgba(52, 152, 219, 0.18)";
    replayContext.fillRect(
      cx - rsu.range_m * pxPerMeter,
      roadY - 10,
      rsu.range_m * 2 * pxPerMeter,
      roadHeight + 20
    );
    replayContext.beginPath();
    replayContext.arc(cx, roadY - 18, 8, 0, Math.PI * 2);
    replayContext.fillStyle = "#3498db";
    replayContext.fill();
    replayContext.fillStyle = "#1f2937";
    replayContext.font = '13px "Instrument Sans", sans-serif';
    replayContext.fillText(rsu.rsu_id, cx - 34, roadY - 34);
  });

  frame.vehicles.forEach((vehicle) => {
    const x = roadLeft + vehicle.x * pxPerMeter;
    const carWidth = 22;
    const carHeight = 14;
    replayContext.fillStyle = statusColor(vehicle.status);
    replayContext.fillRect(x - carWidth / 2, roadY + 6, carWidth, carHeight);
    replayContext.fillStyle = "#111827";
    replayContext.font = '12px "Instrument Sans", sans-serif';
    replayContext.fillText(vehicle.vehicle_id, x - 14, roadY - 8);
  });

  replayStep.textContent = `Step ${frame.step}`;
  replayVehicleCount.textContent = `Vehicles ${frame.vehicles.length}`;
}

function stopReplay() {
  if (replayTimer) {
    clearInterval(replayTimer);
    replayTimer = null;
  }
}

function startReplay({ restartIfComplete = true } = {}) {
  if (!replayData || !replayData.frames || replayData.frames.length === 0) {
    return;
  }

  if (restartIfComplete && replayIndex >= replayData.frames.length - 1) {
    replayIndex = 0;
    drawReplayFrame();
  }

  stopReplay();
  replayTimer = setInterval(() => {
    if (replayIndex >= replayData.frames.length - 1) {
      stopReplay();
      drawReplayFrame();
      return;
    }
    replayIndex += 1;
    drawReplayFrame();
  }, 160 / replaySpeed);
}

function stopLiveReplayPolling() {
  if (liveReplayPoller) {
    clearInterval(liveReplayPoller);
    liveReplayPoller = null;
  }
}

function startLiveReplayPolling() {
  stopLiveReplayPolling();
  liveReplayPoller = setInterval(async () => {
    await refreshRunStatus();
    await refreshRows();
    await refreshTrace({ autoplay: true });
    if (latestRunStatus !== "running") {
      stopLiveReplayPolling();
    }
  }, 1200);
}

async function refreshHealth() {
  backendUrlLabel.textContent = getBackendUrl();
  try {
    const data = await fetchJson("/health");
    backendStatus.textContent = data.status === "ok" ? "Online" : "Unknown";
  } catch (error) {
    backendStatus.textContent = "Offline";
    setMessage(`Backend health check failed: ${error.message}`, "error");
  }
}

async function refreshRunStatus() {
  try {
    const latest = await fetchJson("/runs/latest");
    setRunStatus(latest.status);
    runStartedAt.textContent = latest.started_at
      ? `Started ${formatIstTimestamp(latest.started_at)}`
      : "Not started";
    runFinishedAt.textContent = latest.finished_at
      ? `Finished ${formatIstTimestamp(latest.finished_at)}`
      : "Not finished";
    configPreview.textContent = latest.config
      ? JSON.stringify(latest.config, null, 2)
      : "No run yet.";

    if (latest.error) {
      setMessage(`Run failed: ${latest.error}`, "error");
    } else {
      setMessage(`Latest run status: ${latest.status}.`);
    }
  } catch (error) {
    setMessage(`Could not load latest run: ${error.message}`, "error");
  }
}

function refreshRows() {
  renderTimelineRows(replayData);
}

async function refreshTrace({ autoplay = false } = {}) {
  try {
    const trace = await fetchJson("/runs/latest/trace");
    const nextRunId = trace.meta?.run_id ?? null;
    const nextFrameCount = trace.meta?.frame_count ?? trace.frames?.length ?? 0;
    const isDifferentRun = nextRunId !== replayRunId;
    const hasNewFrames = isDifferentRun || nextFrameCount > replayFrameCount;

    replayData = trace;
    replayRunId = nextRunId;
    replayFrameCount = nextFrameCount;

    if (isDifferentRun) {
      replayIndex = 0;
    }

    if (replayIndex >= replayData.frames.length) {
      replayIndex = Math.max(0, replayData.frames.length - 1);
    }

    drawReplayFrame();
    refreshRows();

    if (autoplay && hasNewFrames) {
      startReplay({ restartIfComplete: false });
    }
  } catch (error) {
    replayData = null;
    replayRunId = null;
    replayFrameCount = 0;
    stopReplay();
    drawReplayFrame();
    refreshRows();
    if (latestRunStatus === "running" && String(error.message).includes("404")) {
      setMessage("Simulation is running. Waiting for the first replay frames...");
      return;
    }
    setMessage(`Could not load replay trace: ${error.message}`, "error");
  }
}

function buildPayload() {
  const formData = new FormData(form);
  return {
    vehicle_count: Number(formData.get("vehicle_count")),
    depart_gap_s: Number(formData.get("depart_gap_s")),
    seed: Number(formData.get("seed")),
    e0_limit_kmph: Number(formData.get("e0_limit_kmph")),
    e1_limit_kmph: Number(formData.get("e1_limit_kmph")),
    e2_limit_kmph: Number(formData.get("e2_limit_kmph")),
    cautious_share: Number(formData.get("cautious_share")),
    aggressive_share: Number(formData.get("aggressive_share")),
    rsu_range_m: Number(formData.get("rsu_range_m")),
    v2v_range_m: Number(formData.get("v2v_range_m")),
    minimum_follow_distance_m: Number(formData.get("minimum_follow_distance_m")),
    step_delay_ms: 0,
    use_gui: false,
  };
}

async function runSimulation(event) {
  event.preventDefault();
  runButton.disabled = true;
  runButton.textContent = "Submitting...";
  backendUrlLabel.textContent = getBackendUrl();
  resetUiState();
  runButton.disabled = true;
  runButton.textContent = "Submitting...";

  try {
    const payload = buildPayload();
    const result = await fetchJson("/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setRunStatus(result.status);
    configPreview.textContent = JSON.stringify(result.config, null, 2);
    setMessage("Simulation started. Live replay will begin automatically as frames arrive.");
    await refreshRunStatus();
    refreshRows();
    await refreshTrace({ autoplay: true });
    startLiveReplayPolling();
  } catch (error) {
    setMessage(`Simulation request failed: ${error.message}`, "error");
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Run Simulation";
  }
}

async function refreshAll() {
  await refreshHealth();
  await refreshRunStatus();
  refreshRows();
  await refreshTrace();
}

form.addEventListener("submit", runSimulation);
refreshButton.addEventListener("click", refreshAll);
backendUrlInput.addEventListener("change", resetUiState);
playReplayButton.addEventListener("click", () => startReplay({ restartIfComplete: true }));
pauseReplayButton.addEventListener("click", stopReplay);
replaySpeedHalfButton.addEventListener("click", () => setReplaySpeed(0.5));
replaySpeedNormalButton.addEventListener("click", () => setReplaySpeed(1));
replaySpeedDoubleButton.addEventListener("click", () => setReplaySpeed(2));
backToTopButton.addEventListener("click", () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
});
window.addEventListener("scroll", updateBackToTopVisibility, { passive: true });

resetUiState();
updateBackToTopVisibility();
