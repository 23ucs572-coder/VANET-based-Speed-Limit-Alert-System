# System Architecture

## Goal

Warn drivers before they enter a lower speed-limit zone by using VANET-style communication.

## Main Components

### 1. Traffic Layer

Handled by `SUMO`.

- vehicles move on the road network
- edges define legal speeds
- routes control traffic demand

### 2. Communication Layer

Handled by `Python + TraCI`.

- RSUs broadcast speed advisories
- vehicles receive and store messages
- vehicles rebroadcast fresh messages to neighbors

### 3. Decision Layer

Handled by `run_simulation.py`.

For each time step, the controller:

- reads vehicle positions and speeds
- checks nearby RSUs
- propagates V2V messages
- compares actual speed against current and upcoming limits
- logs warning events

## Data Flow

```text
SUMO -> TraCI -> Python controller
                 -> RSU broadcast
                 -> V2V relay
                 -> alert generation
                 -> CSV logging
```

## Simplified VANET Assumptions

This starter version assumes:

- fixed RSU communication range
- fixed V2V communication range
- immediate message delivery within range
- TTL-based rebroadcast control
- no MAC-layer collision model

These assumptions are acceptable for a first full-stack prototype.

## Files To Extend First

- `src/run_simulation.py`: main logic
- `scenario/corridor.rou.xml`: traffic demand
- `scenario/corridor.edg.xml`: speed zones

## Recommended Evaluation Metrics

- alert delivery ratio
- average warning lead distance
- overspeed event count
- speed compliance before and after alert
- message count per vehicle
- duplicate message ratio
