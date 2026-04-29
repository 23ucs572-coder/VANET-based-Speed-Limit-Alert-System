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
}

form.addEventListener("submit", runSimulation);
refreshButton.addEventListener("click", refreshAll);
backendUrlInput.addEventListener("change", refreshAll);

refreshAll();
setInterval(refreshRunStatus, 12000);
setInterval(refreshRows, 12000);
