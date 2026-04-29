# VANET-Based Speed Limit Alert System

A SUMO-based VANET simulation with:

- `Python + TraCI` simulation control
- `FastAPI` backend for cloud runs
- static browser frontend for control, replay, and timeline viewing

## What It Does

The project simulates vehicles moving through a three-zone road corridor:

- `e0`: `60 km/h`
- `e1`: `30 km/h`
- `e2`: `50 km/h`

RSUs broadcast speed-limit warnings near zone transitions, and vehicles can forward recent messages to nearby vehicles. The system logs alerts, writes a replay trace, and shows the run in the browser.

## Main Features

- configurable vehicle count, departure gap, and driver mix
- RSU and V2V warning propagation
- non-GUI cloud simulation runs
- live run status from the backend
- browser replay animation
- full per-step simulation timeline table
- replay speed controls

## Project Structure

```text
backend/
  main.py
docs/
  architecture.md
  gui_guide.md
  sources.md
outputs/
  alerts.csv
  latest_trace.json
  runtime/
scenario/
src/
  build_network.py
  launch_app.py
  run_simulation.py
web/
  index.html
  styles.css
  app.js
Dockerfile
render.yaml
README.md
requirements.txt
```

## Local Setup

### Prerequisites

Install:

1. Python `3.11+`
2. SUMO
3. Python packages:

```powershell
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### Build the network

```powershell
python src/build_network.py
```

### Run the simulation

Non-GUI:

```powershell
python src/run_simulation.py
```

GUI:

```powershell
python src/run_simulation.py --gui --delay-ms 600
```

### Desktop launcher

```powershell
python src/launch_app.py
```

## Local Backend

Start the API locally:

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Useful URLs:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API

- `GET /health`
- `GET /config/defaults`
- `GET /runs/latest`
- `GET /runs/latest/alerts`
- `GET /runs/latest/alerts/rows`
- `GET /runs/latest/trace`
- `POST /simulate`

Example `/simulate` request:

```json
{
  "vehicle_count": 8,
  "depart_gap_s": 5,
  "seed": 42,
  "e0_limit_kmph": 60,
  "e1_limit_kmph": 30,
  "e2_limit_kmph": 50,
  "cautious_share": 25,
  "aggressive_share": 35,
  "rsu_range_m": 140,
  "v2v_range_m": 120,
  "minimum_follow_distance_m": 18,
  "step_delay_ms": 0,
  "use_gui": false
}
```

## Frontend

The frontend in [web](D:/Vansec/web) includes:

- `Simulation Controls`
- `Run Status`
- `Simulation Replay`
- `Simulation Timeline`

Current behavior:

- `Run Simulation` starts a backend run
- replay updates from the latest trace
- `Play Simulation Demo` replays the finished run
- timeline shows per-step vehicle history

## Output Files

- [outputs/alerts.csv](D:/Vansec/outputs/alerts.csv)
- [outputs/latest_trace.json](D:/Vansec/outputs/latest_trace.json)
- [outputs/runtime](D:/Vansec/outputs/runtime)

## Render Backend Deployment

This repo already includes:

- [Dockerfile](D:/Vansec/Dockerfile)
- [render.yaml](D:/Vansec/render.yaml)

Render service summary:

```yaml
services:
  - type: web
    name: vanet-sumo-backend
    runtime: docker
    plan: free
    autoDeploy: true
```

Expected backend URL:

```text
https://vanet-sumo-backend.onrender.com
```

### Deploy steps

1. Push repo to GitHub
2. Open Render
3. Create `New -> Blueprint`
4. Connect the repo
5. Render detects `render.yaml`
6. Deploy

### After backend changes

If you update:

- [backend/main.py](D:/Vansec/backend/main.py)
- [src/run_simulation.py](D:/Vansec/src/run_simulation.py)
- [Dockerfile](D:/Vansec/Dockerfile)

push to GitHub:

```powershell
git add .
git commit -m "Update backend"
git push
```

Render will redeploy automatically.

Verify with:

- [https://vanet-sumo-backend.onrender.com/health](https://vanet-sumo-backend.onrender.com/health)
- [https://vanet-sumo-backend.onrender.com/docs](https://vanet-sumo-backend.onrender.com/docs)
- [https://vanet-sumo-backend.onrender.com/runs/latest](https://vanet-sumo-backend.onrender.com/runs/latest)

## Frontend Deployment

The frontend is static and can be deployed on:

- Vercel
- Netlify
- Render Static Sites

Use:

- root directory: `web`
- no build step required

After frontend changes:

```powershell
git add web/index.html web/styles.css web/app.js
git commit -m "Update frontend"
git push
```

## Demo Flow

1. Open the frontend
2. Check backend connection
3. Change parameters
4. Click `Run Simulation`
5. Watch replay and timeline update
6. Replay the finished run with speed controls

## Docs

- [docs/architecture.md](D:/Vansec/docs/architecture.md)
- [docs/gui_guide.md](D:/Vansec/docs/gui_guide.md)
- [docs/sources.md](D:/Vansec/docs/sources.md)
