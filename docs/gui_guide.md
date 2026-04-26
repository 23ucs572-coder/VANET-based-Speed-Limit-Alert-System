# GUI Guide

## Recommended Run Command

```powershell
python D:\Vansec\src\run_simulation.py --gui --delay-ms 600
```

If you want it even slower:

```powershell
python D:\Vansec\src\run_simulation.py --gui --delay-ms 1000
```

## What You Should See

- blue RSU markers above the road
- shaded road sections for different speed zones
- moving vehicles
- green vehicles when compliant
- yellow vehicles when warned
- red vehicles when overspeeding
- live text near vehicles with speed and limit info

## If Text Labels Are Too Small

In SUMO GUI:

1. Press `F9`
2. Open `POI` settings and enable text / type display if the floating labels are hidden
3. Open `vehicle` settings and increase text size
4. Enable vehicle `Show name` if you also want text directly tied to the vehicle object

## Helpful Built-In SUMO Controls

- mouse wheel: zoom
- drag: move the view
- `Home`: fit the whole network
- `Page Up` / `Page Down`: change animation delay
- right-click a vehicle -> `Show Parameter`: inspect detailed speed values

## Reading The Colors

- `Green`: driving within the current limit
- `Yellow`: warned about an upcoming lower limit
- `Red`: currently above the legal speed limit

## Reading The Labels

Each live label is intended to show:

```text
vehicle_id | current_speed | current_limit | overspeed amount | status
```

Example:

```text
veh2 | 72.5 km/h | limit 30 | over +42.5 | SPEEDING
```
