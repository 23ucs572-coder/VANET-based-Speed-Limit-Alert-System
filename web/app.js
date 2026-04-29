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
const replayContext = replayCanvas.getContext("2d");

let replayData = null;
let replayIndex = 0;
let replayTimer = null;

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

function setRunStatus(status) {
  runStatusBadge.textContent = status || "Unknown";
  runStatusBadge.className = "badge";
  if (status === "running") runStatusBadge.classList.add("running");
  if (status === "completed") runStatusBadge.classList.add("completed");
  if (status === "failed") runStatusBadge.classList.add("failed");
  if (status === "idle") runStatusBadge.classList.add("ok");
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${getBackendUrl()}${path}`, options);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return response.json();
}

function renderRows(rows) {
  if (!rows || rows.length === 0) {
    alertsTableBody.innerHTML = `
      <tr>
        <td colspan="11" class="empty-state">No alert rows available yet.</td>
      </tr>
    `;
    return;
  }

  alertsTableBody.innerHTML = rows
    .map((row) => `
      <tr>
        <td>${row.step ?? ""}</td>
        <td>${row.vehicle_id ?? ""}</td>
        <td>${row.event_type ?? ""}</td>
        <td>${row.source ?? ""}</td>
        <td>${row.current_edge ?? ""}</td>
        <td>${row.target_edge ?? ""}</td>
        <td>${row.vehicle_speed_kmph ?? ""}</td>
        <td>${row.limit_kmph ?? ""}</td>
        <td>${row.distance_m ?? ""}</td>
        <td>${row.hops ?? ""}</td>
        <td>${row.details ?? ""}</td>
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

function startReplay() {
  if (!replayData || !replayData.frames || replayData.frames.length === 0) {
    return;
  }
  stopReplay();
  replayTimer = setInterval(() => {
    replayIndex = (replayIndex + 1) % replayData.frames.length;
    drawReplayFrame();
  }, 160);
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
    runStartedAt.textContent = latest.started_at ? `Started ${latest.started_at}` : "Not started";
    runFinishedAt.textContent = latest.finished_at ? `Finished ${latest.finished_at}` : "Not finished";
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

async function refreshRows() {
  try {
    const data = await fetchJson("/runs/latest/alerts/rows?limit=30");
    renderRows(data.rows);
  } catch (error) {
    renderRows([]);
    setMessage(`Could not load alert rows: ${error.message}`, "error");
  }
}

async function refreshTrace() {
  try {
    replayData = await fetchJson("/runs/latest/trace");
    replayIndex = 0;
    drawReplayFrame();
    startReplay();
  } catch (error) {
    replayData = null;
    stopReplay();
    drawReplayFrame();
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

  try {
    const payload = buildPayload();
    const result = await fetchJson("/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setRunStatus(result.status);
    configPreview.textContent = JSON.stringify(result.config, null, 2);
    setMessage("Simulation request accepted. Refreshing status...");
    await refreshAll();
  } catch (error) {
    setMessage(`Simulation request failed: ${error.message}`, "error");
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Run Cloud Simulation";
  }
}

async function refreshAll() {
  await refreshHealth();
  await refreshRunStatus();
  await refreshRows();
  await refreshTrace();
}

form.addEventListener("submit", runSimulation);
refreshButton.addEventListener("click", refreshAll);
backendUrlInput.addEventListener("change", refreshAll);
playReplayButton.addEventListener("click", startReplay);
pauseReplayButton.addEventListener("click", stopReplay);

refreshAll();
setInterval(refreshRunStatus, 12000);
setInterval(refreshRows, 12000);
setInterval(refreshTrace, 15000);
