# VANET-Based Speed Limit Alert System

This starter project shows how to build a VANET-based speed limit alert system with:

- `SUMO` for traffic simulation
- `Python + TraCI` for runtime control
- `RSU -> Vehicle` and `Vehicle -> Vehicle` message propagation
- speed limit warning logs you can use for a report or thesis demo

The project is intentionally small, readable, and easy to extend from scratch.

## What The System Does

Vehicles drive through a corridor with changing speed limits:

- `e0`: 60 km/h
- `e1`: 30 km/h
- `e2`: 50 km/h

Road Side Units (RSUs) broadcast upcoming speed-limit messages near zone changes.
Vehicles that receive a message can rebroadcast it to nearby vehicles, mimicking a
simple VANET dissemination model.

The Python controller checks:

- the vehicle's current speed
- the lane's current legal speed
- whether a lower speed zone is approaching
- whether the alert came from an RSU or another vehicle

Alerts are written to `outputs/alerts.csv`.

## Project Structure

```text
scenario/
  corridor.nod.xml
  corridor.edg.xml
  corridor.rou.xml
  corridor.sumocfg
  corridor.net.xml         
src/
  build_network.py
  run_simulation.py
docs/
  architecture.md
  sources.md
requirements.txt
README.md
backend/
  main.py
  requirements.txt
```

## Prerequisites

1. Install SUMO from the official site.
2. Make sure `sumo` / `sumo-gui` / `netconvert` are on your PATH.
3. Set `SUMO_HOME` if you want to use the tools bundled with SUMO.
4. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

## Quick Start

1. Build the SUMO network:

```powershell
python src/build_network.py
```

2. Run the simulation:

```powershell
python src/run_simulation.py
```

3. Run with the GUI:

```powershell
python src/run_simulation.py --gui --delay-ms 600
```

4. Check the generated alert log:

```text
outputs/alerts.csv
```

## Interactive Launcher

The easiest way to use this project now is the launcher window:

```powershell
python src/launch_app.py
```

From the launcher, you can choose at runtime:

- number of vehicles
- departure gap between vehicles
- speed limits for `e0`, `e1`, and `e2`
- cautious vs aggressive driver mix
- RSU and V2V communication ranges
- GUI animation delay

After you click `Launch SUMO Simulation`, the project will:

1. generate a fresh route file from your chosen parameters
2. start SUMO with the GUI
3. apply your road speed limits dynamically
4. show the updated overlays, labels, colors, and warnings

## Better GUI View

For a slower, easier-to-watch animation:

```powershell
python src/run_simulation.py --gui --delay-ms 600
```

The enhanced GUI includes:

- RSU markers and coverage areas
- colored road zones for 60 / 30 / 50 km/h segments
- red vehicles when speeding
- yellow vehicles when warned about an upcoming lower limit
- live camera tracking of the lead vehicle
- dynamic text labels near vehicles

Extra SUMO GUI tips are in:

- [docs/gui_guide.md](D:\Vansec\docs\gui_guide.md)

## How It Works

1. `build_network.py` calls `netconvert` on the node and edge files.
2. `run_simulation.py` starts SUMO through TraCI.
3. RSUs broadcast speed-limit messages to vehicles in range.
4. Vehicles rebroadcast recent messages to neighbors.
5. The controller logs:
   - message deliveries
   - current overspeed warnings
   - upcoming speed-zone warnings

## Put It On GitHub

1. Create a new empty repository on GitHub.
2. Open PowerShell in `D:\Vansec`.
3. Run these commands one by one:

```powershell
git init
git add .
git commit -m "Initial VANET SUMO project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

After that, your project is on GitHub and future changes can be pushed with:

```powershell
git add .
git commit -m "Describe your change"
git push
```

## SUMO Backend Starter

The project now also includes a small FastAPI backend starter:

- [backend/main.py](D:\Vansec\backend\main.py)
- [backend/requirements.txt](D:\Vansec\backend\requirements.txt)

This backend is the first step toward a web-deployable version.

### Install backend packages

```powershell
python -m pip install -r D:\Vansec\backend\requirements.txt
```

### Start the backend locally

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Open it in your browser

- API home: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### What the backend can do now

- `/health`
  Checks that the backend is alive
- `/config/defaults`
  Returns default simulation settings
- `/runs/latest`
  Shows the latest run status
- `/simulate`
  Starts one non-GUI simulation run in the background

Example JSON body for `/simulate`:

```json
{
  "vehicle_count": 12,
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

Important:
- for internet deployment later, the backend should run `use_gui = false`
- the current Tkinter launcher and SUMO GUI remain your local desktop version
- the backend is the starting point for a future frontend website

## Deploy The Backend Online

The easiest deploy path for the current repo is:

- `GitHub` for source control
- `Render` or `Railway` for the FastAPI + SUMO backend
- `Netlify` later for a separate frontend site

This repo now includes:

- [Dockerfile](D:\Vansec\Dockerfile)
- [render.yaml](D:\Vansec\render.yaml)

These let a cloud host install SUMO and run the backend without using your local CPU.

### Render

1. Create an account on [Render](https://render.com/)
2. Click `New` -> `Blueprint`
3. Connect your GitHub account
4. Choose your repo:
   `23ucs572-coder/VANET-based-Speed-Limit-Alert-System`
5. Render should detect [render.yaml](D:\Vansec\render.yaml)
6. Confirm the deploy

After deployment, Render will give you a public URL like:

```text
https://vanet-sumo-backend.onrender.com
```

Render rebuilds and redeploys automatically whenever you push to your GitHub `main` branch.

### Railway

If you prefer Railway:

1. Create an account on [Railway](https://railway.com/)
2. Choose `New Project`
3. Select `Deploy from GitHub repo`
4. Pick your repo
5. Railway will build from the included [Dockerfile](D:\Vansec\Dockerfile)
6. Add a public domain to the service

### Netlify

Netlify is best used for the future frontend, not for the SUMO backend itself.

Right now, this repo does not yet contain a browser frontend, so there is nothing meaningful to deploy to Netlify yet.
The present public link should come from Render or Railway first.

## Suggested Full-Project Roadmap

If you want to turn this into a strong university or portfolio project, build it in phases:

1. Baseline:
   Run the current corridor demo and validate that alerts appear correctly.
2. Better VANET model:
   Add packet loss, delay, channel congestion, or rebroadcast suppression.
3. Larger road network:
   Import a real map from OpenStreetMap into SUMO.
4. Stronger analytics:
   Measure alert latency, warning success rate, overspeed reduction, and message overhead.
5. UI/reporting:
   Plot speed profiles, alert counts, and dissemination coverage.
6. Research comparison:
   Compare `RSU only`, `RSU + V2V`, and `no alert` scenarios.

## Good Next Extensions

- add driver classes: cautious, normal, aggressive
- add dynamic speed limits for weather or school zones
- integrate confidence scoring for received messages
- add malicious or stale-message detection
- export charts from the CSV logs
- couple SUMO with a dedicated network simulator later if needed

## Notes

- This project uses a lightweight VANET logic inside Python rather than a full wireless PHY/MAC simulator.
- That makes it a good starting point for learning, demos, and early research prototypes.
- For higher-fidelity networking, you can later couple SUMO with ns-3 or OMNeT++.

## Sources

See:

- [docs/architecture.md](D:\Vansec\docs\architecture.md)
- [docs/sources.md](D:\Vansec\docs\sources.md)
