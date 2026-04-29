from __future__ import annotations

import csv
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.run_simulation import (
    OUTPUT_DIR,
    RUNTIME_DIR,
    TRACE_FILE,
    SimulationConfig,
    default_config,
    run_simulation,
)


app = FastAPI(
    title="VANET SUMO Backend",
    version="0.1.0",
    description=(
        "Starter API for running the VANET-based speed limit alert simulation "
        "without the desktop launcher."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

run_lock = threading.Lock()
latest_run: dict[str, object] = {
    "run_id": None,
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "config": None,
    "alert_file": str(OUTPUT_DIR / "alerts.csv"),
    "runtime_dir": str(RUNTIME_DIR),
    "error": None,
}


def _force_release_lock() -> None:
    """Release the run lock if it is currently held (for stuck/crashed runs)."""
    try:
        run_lock.release()
    except RuntimeError:
        pass  # already unlocked — that's fine


class SimulationRequest(BaseModel):
    vehicle_count: int = Field(12, ge=1, le=200)
    depart_gap_s: int = Field(5, ge=1, le=120)
    seed: int = 42
    e0_limit_kmph: int = Field(60, ge=10, le=140)
    e1_limit_kmph: int = Field(30, ge=10, le=140)
    e2_limit_kmph: int = Field(50, ge=10, le=140)
    cautious_share: int = Field(25, ge=0, le=100)
    aggressive_share: int = Field(35, ge=0, le=100)
    rsu_range_m: int = Field(140, ge=20, le=500)
    v2v_range_m: int = Field(120, ge=20, le=500)
    minimum_follow_distance_m: int = Field(18, ge=5, le=100)
    step_delay_ms: int = Field(0, ge=0, le=5000)
    use_gui: bool = False


class SimulationRunState(BaseModel):
    run_id: str | None
    status: Literal["idle", "running", "completed", "failed"]
    started_at: str | None
    finished_at: str | None
    config: dict | None
    alert_file: str
    runtime_dir: str
    error: str | None


def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _request_to_config(request: SimulationRequest) -> SimulationConfig:
    cautious_share = max(0, min(request.cautious_share, 100))
    aggressive_share = max(0, min(request.aggressive_share, 100 - cautious_share))
    return SimulationConfig(
        use_gui=request.use_gui,
        step_delay_ms=request.step_delay_ms,
        vehicle_count=request.vehicle_count,
        depart_gap_s=request.depart_gap_s,
        seed=request.seed,
        e0_limit_kmph=request.e0_limit_kmph,
        e1_limit_kmph=request.e1_limit_kmph,
        e2_limit_kmph=request.e2_limit_kmph,
        cautious_share=cautious_share,
        aggressive_share=aggressive_share,
        rsu_range_m=request.rsu_range_m,
        v2v_range_m=request.v2v_range_m,
        minimum_follow_distance_m=request.minimum_follow_distance_m,
    )


def _run_in_background(config: SimulationConfig, run_id: str) -> None:
    if not run_lock.acquire(blocking=False):
        return

    try:
        TRACE_FILE.unlink(missing_ok=True)
        latest_run["run_id"] = run_id
        latest_run["status"] = "running"
        latest_run["started_at"] = _timestamp()
        latest_run["finished_at"] = None
        latest_run["config"] = config.__dict__.copy()
        latest_run["error"] = None
        run_simulation(config, run_id=run_id)
        latest_run["status"] = "completed"
        latest_run["finished_at"] = _timestamp()
    except Exception as exc:
        latest_run["status"] = "failed"
        latest_run["finished_at"] = _timestamp()
        latest_run["error"] = str(exc)
    finally:
        # Always release — even if run_simulation raised SystemExit or BaseException
        try:
            run_lock.release()
        except RuntimeError:
            pass


@app.get("/")
def root() -> dict[str, object]:
    return {
        "message": "VANET SUMO backend is running.",
        "docs": "/docs",
        "health": "/health",
        "defaults": "/config/defaults",
        "latest_run": "/runs/latest",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/simulate/reset")
def reset_simulation() -> dict[str, str]:
    """Force-clear a stuck simulation lock so a new run can be submitted."""
    was_locked = run_lock.locked()
    _force_release_lock()
    latest_run["status"] = "failed"
    latest_run["finished_at"] = _timestamp()
    if latest_run.get("error") is None:
        latest_run["error"] = "Manually reset by user."
    return {
        "message": "Lock cleared." if was_locked else "Lock was already free.",
        "status": "idle",
    }


@app.get("/config/defaults")
def config_defaults() -> dict[str, object]:
    config = default_config()
    return {
        "vehicle_count": config.vehicle_count,
        "depart_gap_s": config.depart_gap_s,
        "seed": config.seed,
        "e0_limit_kmph": config.e0_limit_kmph,
        "e1_limit_kmph": config.e1_limit_kmph,
        "e2_limit_kmph": config.e2_limit_kmph,
        "cautious_share": config.cautious_share,
        "aggressive_share": config.aggressive_share,
        "rsu_range_m": config.rsu_range_m,
        "v2v_range_m": config.v2v_range_m,
        "minimum_follow_distance_m": config.minimum_follow_distance_m,
        "step_delay_ms": 0,
        "use_gui": False,
    }


@app.get("/runs/latest", response_model=SimulationRunState)
def get_latest_run() -> SimulationRunState:
    return SimulationRunState(**latest_run)


@app.get("/runs/latest/alerts")
def get_latest_alerts() -> dict[str, object]:
    alert_file = Path(str(latest_run["alert_file"]))
    if not alert_file.exists():
        raise HTTPException(status_code=404, detail="No alerts.csv file found yet.")
    return {
        "alert_file": str(alert_file),
        "size_bytes": alert_file.stat().st_size,
    }


@app.get("/runs/latest/alerts/rows")
def get_latest_alert_rows(limit: int | None = None) -> dict[str, object]:
    alert_file = Path(str(latest_run["alert_file"]))
    if not alert_file.exists():
        raise HTTPException(status_code=404, detail="No alerts.csv file found yet.")

    with alert_file.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    total_rows = len(rows)

    if limit is not None:
        safe_limit = max(1, min(limit, 5000))
        rows = rows[-safe_limit:]

    return {
        "alert_file": str(alert_file),
        "total_rows": total_rows,
        "rows": rows,
    }


@app.get("/runs/latest/trace")
def get_latest_trace() -> dict[str, object]:
    if not TRACE_FILE.exists():
        raise HTTPException(status_code=404, detail="No replay trace found yet.")
    return json.loads(TRACE_FILE.read_text(encoding="utf-8"))


@app.post("/simulate", response_model=SimulationRunState)
def simulate(request: SimulationRequest, background_tasks: BackgroundTasks) -> SimulationRunState:
    # If the previous run failed or completed but left the lock held, auto-release it.
    if run_lock.locked() and latest_run.get("status") in {"failed", "completed"}:
        _force_release_lock()

    if run_lock.locked():
        raise HTTPException(status_code=409, detail="A simulation is already running.")

    config = _request_to_config(request)
    run_id = _timestamp()
    background_tasks.add_task(_run_in_background, config, run_id)

    queued_state = latest_run.copy()
    queued_state["run_id"] = run_id
    queued_state["status"] = "running"
    queued_state["started_at"] = _timestamp()
    queued_state["finished_at"] = None
    queued_state["config"] = config.__dict__.copy()
    queued_state["error"] = None
    latest_run.update(queued_state)
    return SimulationRunState(**queued_state)
