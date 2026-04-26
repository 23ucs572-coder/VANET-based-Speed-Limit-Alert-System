from __future__ import annotations

import argparse
import csv
import math
import os
import random
import shutil
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = ROOT / "scenario"
OUTPUT_DIR = ROOT / "outputs"
RUNTIME_DIR = OUTPUT_DIR / "runtime"
SUMO_CONFIG = SCENARIO_DIR / "corridor.sumocfg"
NETWORK_FILE = SCENARIO_DIR / "corridor.net.xml"


if "SUMO_HOME" in os.environ:
    tools_path = Path(os.environ["SUMO_HOME"]) / "tools"
    if str(tools_path) not in sys.path:
        sys.path.append(str(tools_path))


MPS_TO_KMPH = 3.6
KMPH_TO_MPS = 1 / 3.6
GUI_VIEW_ID = "View #0"
ROAD_LENGTH = 1200.0
EDGE_LENGTH = 400.0

COLOR_OK = (46, 204, 113, 255)
COLOR_WARNED = (241, 196, 15, 255)
COLOR_SPEEDING = (231, 76, 60, 255)
COLOR_DANGER = (255, 120, 40, 255)
COLOR_RSU = (52, 152, 219, 255)
COLOR_RSU_RANGE = (52, 152, 219, 45)
COLOR_ZONE_A = (81, 120, 186, 35)
COLOR_ZONE_B = (255, 214, 10, 65)
COLOR_ZONE_C = (72, 201, 176, 55)
COLOR_TEXT = (20, 20, 20, 255)
COLOR_PANEL_BG = (255, 255, 255, 245)
COLOR_PANEL_BORDER = (210, 216, 226, 90)

EDGE_SEQUENCE = ("e0", "e1", "e2")
EDGE_TO_LANE = {"e0": "e0_0", "e1": "e1_0", "e2": "e2_0"}


@dataclass(frozen=True)
class SpeedLimitMessage:
    message_id: str
    origin_type: str
    origin_id: str
    approach_edge: str
    target_edge: str
    target_limit_mps: float
    issued_step: int
    ttl_steps: int
    hops: int


@dataclass(frozen=True)
class SafetyMessage:
    message_id: str
    origin_id: str
    risk_edge: str
    issued_step: int
    ttl_steps: int
    hops: int
    recommended_speed_mps: float
    reason: str


@dataclass
class VehicleMemory:
    known_messages: dict[str, SpeedLimitMessage] = field(default_factory=dict)
    known_safety_messages: dict[str, SafetyMessage] = field(default_factory=dict)
    last_forwarded: dict[str, int] = field(default_factory=dict)
    last_alert_step: dict[str, int] = field(default_factory=dict)
    status: str = "ok"


@dataclass(frozen=True)
class RSU:
    rsu_id: str
    x: float
    y: float
    broadcast_range_m: float
    approach_edge: str
    target_edge: str
    target_limit_mps: float


@dataclass(frozen=True)
class SimulationConfig:
    use_gui: bool = True
    step_delay_ms: int = 600
    vehicle_count: int = 12
    depart_gap_s: int = 5
    seed: int = 42
    e0_limit_kmph: int = 60
    e1_limit_kmph: int = 30
    e2_limit_kmph: int = 50
    cautious_share: int = 25
    aggressive_share: int = 35
    rsu_range_m: int = 140
    v2v_range_m: int = 120
    ttl_steps: int = 25
    safety_gap_m: int = 22
    minimum_follow_distance_m: int = 18
    harsh_brake_threshold_mps2: float = 2.8

    @property
    def road_limits_kmph(self) -> dict[str, int]:
        return {
            "e0": self.e0_limit_kmph,
            "e1": self.e1_limit_kmph,
            "e2": self.e2_limit_kmph,
        }

    @property
    def road_limits_mps(self) -> dict[str, float]:
        return {edge: value * KMPH_TO_MPS for edge, value in self.road_limits_kmph.items()}

    @property
    def normal_share(self) -> int:
        return max(0, 100 - self.cautious_share - self.aggressive_share)

    @property
    def simulation_end_s(self) -> int:
        base = self.vehicle_count * self.depart_gap_s + 200
        return max(200, base)


def default_config() -> SimulationConfig:
    return SimulationConfig()


def kmph(value_mps: float) -> float:
    return value_mps * MPS_TO_KMPH


def mps(value_kmph: float) -> float:
    return value_kmph * KMPH_TO_MPS


def euclidean(a_x: float, a_y: float, b_x: float, b_y: float) -> float:
    return math.hypot(a_x - b_x, a_y - b_y)


def offset_point(x: float, y: float, dx: float = 0.0, dy: float = 0.0) -> tuple[float, float]:
    return (x + dx, y + dy)


def get_sumo_binary(use_gui: bool) -> str:
    binary_name = "sumo-gui" if use_gui else "sumo"
    binary = shutil.which(binary_name)
    if binary is None:
        raise SystemExit(
            f"'{binary_name}' was not found on PATH. Install SUMO and expose it on PATH."
        )
    return binary


def ensure_network_exists() -> None:
    if NETWORK_FILE.exists():
        return
    raise SystemExit(
        f"Missing network file: {NETWORK_FILE}\n"
        "Run `python src/build_network.py` first."
    )


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    RUNTIME_DIR.mkdir(exist_ok=True)


def get_rsus(config: SimulationConfig) -> list[RSU]:
    limits = config.road_limits_mps
    return [
        RSU(
            rsu_id="rsu_school_zone",
            x=360.0,
            y=0.0,
            broadcast_range_m=float(config.rsu_range_m),
            approach_edge="e0",
            target_edge="e1",
            target_limit_mps=limits["e1"],
        ),
        RSU(
            rsu_id="rsu_recovery_zone",
            x=760.0,
            y=0.0,
            broadcast_range_m=float(config.rsu_range_m),
            approach_edge="e1",
            target_edge="e2",
            target_limit_mps=limits["e2"],
        ),
    ]


def write_event(writer: csv.DictWriter, row: dict[str, object]) -> None:
    writer.writerow(row)


def best_message_for_vehicle(
    memory: VehicleMemory, current_step: int
) -> SpeedLimitMessage | None:
    active = [
        msg
        for msg in memory.known_messages.values()
        if current_step - msg.issued_step <= msg.ttl_steps
    ]
    if not active:
        return None
    return sorted(active, key=lambda item: (item.issued_step, -item.hops), reverse=True)[0]


def accept_message(
    memory: VehicleMemory, message: SpeedLimitMessage, current_step: int
) -> bool:
    existing = memory.known_messages.get(message.target_edge)
    if existing is None:
        memory.known_messages[message.target_edge] = message
        return True

    should_replace = (
        message.issued_step > existing.issued_step
        or (
            message.issued_step == existing.issued_step and message.hops < existing.hops
        )
    )
    if should_replace and current_step - message.issued_step <= message.ttl_steps:
        memory.known_messages[message.target_edge] = message
        return True
    return False


def best_safety_message(
    memory: VehicleMemory, current_step: int
) -> SafetyMessage | None:
    active = [
        msg
        for msg in memory.known_safety_messages.values()
        if current_step - msg.issued_step <= msg.ttl_steps
    ]
    if not active:
        return None
    return sorted(active, key=lambda item: (item.issued_step, -item.hops), reverse=True)[0]


def accept_safety_message(
    memory: VehicleMemory, message: SafetyMessage, current_step: int
) -> bool:
    existing = memory.known_safety_messages.get(message.risk_edge)
    if existing is None:
        memory.known_safety_messages[message.risk_edge] = message
        return True
    should_replace = (
        message.issued_step > existing.issued_step
        or (
            message.issued_step == existing.issued_step and message.hops < existing.hops
        )
    )
    if should_replace and current_step - message.issued_step <= message.ttl_steps:
        memory.known_safety_messages[message.risk_edge] = message
        return True
    return False


def should_emit_alert(
    memory: VehicleMemory, alert_key: str, current_step: int, cooldown_steps: int = 5
) -> bool:
    last_step = memory.last_alert_step.get(alert_key, -10_000)
    if current_step - last_step >= cooldown_steps:
        memory.last_alert_step[alert_key] = current_step
        return True
    return False


def distribute_vehicle_types(config: SimulationConfig) -> list[str]:
    rng = random.Random(config.seed)
    vehicle_types: list[str] = []
    normal_share = config.normal_share
    weighted_pool = (
        ["cautious"] * max(1, config.cautious_share)
        + ["normal"] * max(1, normal_share)
        + ["aggressive"] * max(1, config.aggressive_share)
    )
    for _ in range(config.vehicle_count):
        vehicle_types.append(rng.choice(weighted_pool))
    return vehicle_types


def build_route_file(config: SimulationConfig) -> Path:
    ensure_output_dirs()
    route_path = RUNTIME_DIR / "generated_routes.rou.xml"
    vehicle_types = distribute_vehicle_types(config)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<routes>",
        '    <vType id="cautious" accel="1.8" decel="4.5" sigma="0.3" length="5.0" minGap="2.5" maxSpeed="18.0" speedFactor="0.92" color="46,204,113"/>',
        '    <vType id="normal" accel="2.4" decel="4.5" sigma="0.5" length="5.0" minGap="2.5" maxSpeed="22.0" speedFactor="1.02" color="52,152,219"/>',
        '    <vType id="aggressive" accel="3.0" decel="5.0" sigma="0.8" length="5.0" minGap="2.0" maxSpeed="30.0" speedFactor="1.22" color="231,76,60"/>',
        '    <route id="main_corridor" edges="e0 e1 e2"/>',
    ]
    for index, vehicle_type in enumerate(vehicle_types):
        depart = index * config.depart_gap_s
        lines.append(
            f'    <vehicle id="veh{index}" type="{escape(vehicle_type)}" route="main_corridor" '
            f'depart="{depart}" departSpeed="max"/>'
        )
    lines.append("</routes>")
    route_path.write_text("\n".join(lines), encoding="utf-8")
    return route_path


def add_gui_overlays(traci, config: SimulationConfig, rsus: list[RSU]) -> None:
    road_labels = {
        "e0": (0.0, 400.0, COLOR_ZONE_A, config.e0_limit_kmph, "Approach Zone"),
        "e1": (400.0, 800.0, COLOR_ZONE_B, config.e1_limit_kmph, "School Zone"),
        "e2": (800.0, 1200.0, COLOR_ZONE_C, config.e2_limit_kmph, "Recovery Zone"),
    }

    for edge_id, (start_x, end_x, color, speed_limit, label) in road_labels.items():
        traci.polygon.add(
            f"zone_{edge_id}",
            [(start_x, -15.0), (end_x, -15.0), (end_x, 15.0), (start_x, 15.0)],
            color,
            fill=True,
            polygonType="",
            layer=1,
            lineWidth=1,
        )
        traci.poi.add(
            f"speed_label_{edge_id}",
            (start_x + end_x) / 2,
            34.0,
            (0, 0, 0, 0),
            poiType=f"{edge_id.upper()} | {label} | {speed_limit} km/h",
            layer=7,
            width=0.0,
            height=0.0,
        )

    legend = [
        ("legend_ok", 65.0, 70.0, "Green = within current limit"),
        ("legend_warn", 320.0, 70.0, "Yellow = warned about upcoming lower limit"),
        ("legend_speed", 760.0, 70.0, "Red = overspeeding now"),
        ("legend_danger", 1040.0, 70.0, "Orange = collision warning"),
        (
            "legend_cfg",
            200.0,
            -18.0,
            (
                f"Vehicles {config.vehicle_count} | Gap {config.depart_gap_s}s | "
                f"RSU {config.rsu_range_m}m | V2V {config.v2v_range_m}m | "
                f"Min follow {config.minimum_follow_distance_m}m"
            ),
        ),
    ]
    for poi_id, x_pos, y_pos, text in legend:
        traci.poi.add(
            poi_id,
            x_pos,
            y_pos,
            (0, 0, 0, 0),
            poiType=text,
            layer=7,
            width=0.0,
            height=0.0,
        )

    for rsu in rsus:
        traci.poi.add(
            rsu.rsu_id,
            rsu.x,
            rsu.y + 20.0,
            COLOR_RSU,
            poiType=(
                f"{rsu.rsu_id.replace('_', ' ').title()} | "
                f"warn next {kmph(rsu.target_limit_mps):.0f} km/h"
            ),
            layer=8,
            width=0.0,
            height=0.0,
        )
        traci.polygon.add(
            f"{rsu.rsu_id}_range",
            [
                (rsu.x - rsu.broadcast_range_m, -8.0),
                (rsu.x + rsu.broadcast_range_m, -8.0),
                (rsu.x + rsu.broadcast_range_m, 8.0),
                (rsu.x - rsu.broadcast_range_m, 8.0),
            ],
            COLOR_RSU_RANGE,
            fill=True,
            polygonType="",
            layer=2,
            lineWidth=1,
        )


def setup_gui_view(traci) -> None:
    traci.gui.setBoundary(GUI_VIEW_ID, -40.0, -90.0, 1240.0, 110.0)


def apply_runtime_speed_limits(traci, config: SimulationConfig) -> None:
    for edge_id, speed_limit in config.road_limits_mps.items():
        traci.lane.setMaxSpeed(EDGE_TO_LANE[edge_id], speed_limit)


def update_vehicle_visuals(traci, vehicle_id: str, memory: VehicleMemory, speed_mps: float) -> None:
    if memory.status == "speeding":
        traci.vehicle.setColor(vehicle_id, COLOR_SPEEDING)
    elif memory.status == "warned":
        traci.vehicle.setColor(vehicle_id, COLOR_WARNED)
    elif memory.status == "danger":
        traci.vehicle.setColor(vehicle_id, COLOR_DANGER)
    else:
        traci.vehicle.setColor(vehicle_id, COLOR_OK)


def update_vehicle_text_and_table(
    traci,
    vehicle_ids: list[str],
    memories: dict[str, VehicleMemory],
) -> None:
    for vehicle_id in vehicle_ids:
        x_pos, y_pos = traci.vehicle.getPosition(vehicle_id)
        poi_id = f"veh_label_{vehicle_id}"
        label_x, label_y = offset_point(x_pos, y_pos, 0.0, 10.0)
        if poi_id not in traci.poi.getIDList():
            traci.poi.add(
                poi_id,
                label_x,
                label_y,
                (0, 0, 0, 0),
                poiType=vehicle_id,
                layer=9,
                width=1.0,
                height=1.0,
            )
        else:
            traci.poi.setPosition(poi_id, label_x, label_y)
            traci.poi.setType(poi_id, vehicle_id)
            traci.poi.setColor(poi_id, COLOR_TEXT)

    info_ids = [poi_id for poi_id in traci.poi.getIDList() if poi_id.startswith("table_")]
    for poi_id in info_ids:
        traci.poi.remove(poi_id, 11)

    ordered = sorted(
        vehicle_ids,
        key=lambda veh_id: int(veh_id.removeprefix("veh")) if veh_id.startswith("veh") else 0,
    )
    rows = []
    for vehicle_id in ordered:
        speed_kmph = kmph(traci.vehicle.getSpeed(vehicle_id))
        lane_limit_kmph = kmph(traci.lane.getMaxSpeed(traci.vehicle.getLaneID(vehicle_id)))
        over_by = max(0.0, speed_kmph - lane_limit_kmph)
        status = memories[vehicle_id].status.upper()
        rows.append((vehicle_id, speed_kmph, lane_limit_kmph, over_by, status))

    rows_per_column = 12
    left_count = min(len(rows), rows_per_column)
    right_count = max(0, len(rows) - rows_per_column)
    max_row_count = max(left_count, right_count, 1)
    panel_left = 116.0
    panel_top = -38.0
    panel_bottom = -82.0 - ((max_row_count - 1) * 12.0) - 8.0
    panel_right = 620.0 if right_count == 0 else 1220.0

    if "vehicle_info_panel_bg" not in traci.polygon.getIDList():
        traci.polygon.add(
            "vehicle_info_panel_bg",
            [
                (panel_left, panel_bottom),
                (panel_right, panel_bottom),
                (panel_right, panel_top),
                (panel_left, panel_top),
            ],
            COLOR_PANEL_BG,
            fill=True,
            polygonType="Vehicle information panel",
            layer=3,
            lineWidth=1,
        )
    else:
        traci.polygon.setShape(
            "vehicle_info_panel_bg",
            [
                (panel_left, panel_bottom),
                (panel_right, panel_bottom),
                (panel_right, panel_top),
                (panel_left, panel_top),
            ],
        )
    traci.polygon.setType("vehicle_info_panel_bg", "")

    if "vehicle_info_panel_border" not in traci.polygon.getIDList():
        traci.polygon.add(
            "vehicle_info_panel_border",
            [
                (panel_left, panel_bottom),
                (panel_right, panel_bottom),
                (panel_right, panel_top),
                (panel_left, panel_top),
            ],
            COLOR_PANEL_BORDER,
            fill=False,
            polygonType="Vehicle information panel border",
            layer=4,
            lineWidth=1,
        )
    else:
        traci.polygon.setShape(
            "vehicle_info_panel_border",
            [
                (panel_left, panel_bottom),
                (panel_right, panel_bottom),
                (panel_right, panel_top),
                (panel_left, panel_top),
            ],
        )
    traci.polygon.setType("vehicle_info_panel_border", "")

    header_lines = [
        ("table_title", 364.0, -42.0, "Vehicle Information Table", COLOR_TEXT),
        ("table_head_l", 364.0, -56.0, "ID       SPD   LIM   OVR   STATUS", COLOR_TEXT),
        ("table_key_1", 980.0, -42.0, "ID = Vehicle ID", COLOR_TEXT),
        ("table_key_2", 980.0, -54.0, "SPD = Speed", COLOR_TEXT),
        ("table_key_3", 980.0, -66.0, "LIM = Speed Limit", COLOR_TEXT),
        ("table_key_4", 980.0, -78.0, "OVR = Over Limit", COLOR_TEXT),
        ("table_key_5", 980.0, -90.0, "STATUS = Vehicle State", COLOR_TEXT),
    ]
    for poi_id, x_pos, y_pos, text, color in header_lines:
        if poi_id not in traci.poi.getIDList():
            traci.poi.add(
                poi_id,
                x_pos,
                y_pos,
                (0, 0, 0, 0),
                poiType=text,
                layer=11,
                width=0.0,
                height=0.0,
            )
        else:
            traci.poi.setPosition(poi_id, x_pos, y_pos)
            traci.poi.setType(poi_id, text)
        traci.poi.setColor(poi_id, color)

    for index, (vehicle_id, speed_kmph, lane_limit_kmph, over_by, status) in enumerate(rows):
        column = 0 if index < rows_per_column else 1
        row_index = index if index < rows_per_column else index - rows_per_column
        x_pos = 364.0 if column == 0 else 984.0
        y_pos = -72.0 - (row_index * 12.0)
        text = f"{vehicle_id:<8} {speed_kmph:>3.0f}   {lane_limit_kmph:>3.0f}   {over_by:>3.0f}   {status}"
        poi_id = f"table_{index}"
        traci.poi.add(
            poi_id,
            x_pos,
            y_pos,
            (0, 0, 0, 0),
            poiType=text,
            layer=11,
            width=0.0,
            height=0.0,
        )
        line_color = {
            "DANGER": COLOR_DANGER,
            "SPEEDING": COLOR_SPEEDING,
            "WARNED": COLOR_WARNED,
        }.get(status, COLOR_TEXT)
        traci.poi.setColor(poi_id, line_color)


def update_dashboard_text(
    traci,
    step: int,
    vehicle_ids: list[str],
    memories: dict[str, VehicleMemory],
    config: SimulationConfig,
) -> None:
    speeding = sum(1 for veh_id in vehicle_ids if memories[veh_id].status == "speeding")
    warned = sum(1 for veh_id in vehicle_ids if memories[veh_id].status == "warned")
    danger = sum(1 for veh_id in vehicle_ids if memories[veh_id].status == "danger")
    compliant = max(0, len(vehicle_ids) - speeding - warned - danger)
    text = (
        f"Step {step} | On road {len(vehicle_ids)} | "
        f"Compliant {compliant} | Warned {warned} | Danger {danger} | Speeding {speeding} | "
        f"Road limits {config.e0_limit_kmph}/{config.e1_limit_kmph}/{config.e2_limit_kmph} km/h"
    )
    poi_id = "dashboard_status"
    if poi_id not in traci.poi.getIDList():
        traci.poi.add(
            poi_id,
            600.0,
            88.0,
            (0, 0, 0, 0),
            poiType=text,
            layer=12,
            width=0.0,
            height=0.0,
        )
    else:
        traci.poi.setType(poi_id, text)


def remove_departed_vehicle_labels(traci, active_vehicle_ids: Iterable[str]) -> None:
    active = set(active_vehicle_ids)
    for poi_id in list(traci.poi.getIDList()):
        if not poi_id.startswith("veh_label_"):
            continue
        vehicle_id = poi_id.removeprefix("veh_label_")
        if vehicle_id not in active:
            traci.poi.remove(poi_id, 9)


def build_sumo_command(
    config: SimulationConfig,
    route_file: Path,
) -> list[str]:
    sumo_binary = get_sumo_binary(config.use_gui)
    command = [
        sumo_binary,
        "-c",
        str(SUMO_CONFIG),
        "--route-files",
        str(route_file),
        "--end",
        str(config.simulation_end_s),
    ]
    if config.use_gui:
        command.extend(["--start", "--delay", str(max(config.step_delay_ms, 0))])
    return command


def run_simulation(config: SimulationConfig) -> None:
    try:
        import traci
    except ImportError as exc:
        raise SystemExit(
            "Unable to import traci. Install SUMO / traci and set SUMO_HOME if needed."
        ) from exc

    ensure_network_exists()
    ensure_output_dirs()

    route_file = build_route_file(config)
    rsus = get_rsus(config)
    sumo_cmd = build_sumo_command(config, route_file)

    traci.start(sumo_cmd)
    apply_runtime_speed_limits(traci, config)
    if config.use_gui:
        add_gui_overlays(traci, config, rsus)
        setup_gui_view(traci)

    memories: dict[str, VehicleMemory] = {}
    alert_file = OUTPUT_DIR / "alerts.csv"

    with alert_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "step",
                "vehicle_id",
                "event_type",
                "source",
                "current_edge",
                "target_edge",
                "vehicle_speed_kmph",
                "limit_kmph",
                "distance_m",
                "message_id",
                "hops",
                "details",
            ],
        )
        writer.writeheader()

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            if config.use_gui and config.step_delay_ms > 0:
                time.sleep(config.step_delay_ms / 1000.0)

            step = int(traci.simulation.getTime())
            vehicle_ids = traci.vehicle.getIDList()

            for vehicle_id in vehicle_ids:
                memories.setdefault(vehicle_id, VehicleMemory())
                memories[vehicle_id].status = "ok"

            vehicle_positions = {
                vehicle_id: traci.vehicle.getPosition(vehicle_id) for vehicle_id in vehicle_ids
            }

            for rsu in rsus:
                base_message = SpeedLimitMessage(
                    message_id=f"{rsu.rsu_id}@{step}",
                    origin_type="rsu",
                    origin_id=rsu.rsu_id,
                    approach_edge=rsu.approach_edge,
                    target_edge=rsu.target_edge,
                    target_limit_mps=rsu.target_limit_mps,
                    issued_step=step,
                    ttl_steps=config.ttl_steps,
                    hops=0,
                )
                for vehicle_id in vehicle_ids:
                    current_edge = traci.vehicle.getRoadID(vehicle_id)
                    if current_edge != rsu.approach_edge:
                        continue

                    x_pos, y_pos = vehicle_positions[vehicle_id]
                    distance = euclidean(x_pos, y_pos, rsu.x, rsu.y)
                    if distance > rsu.broadcast_range_m:
                        continue

                    memory = memories[vehicle_id]
                    if accept_message(memory, base_message, step):
                        write_event(
                            writer,
                            {
                                "step": step,
                                "vehicle_id": vehicle_id,
                                "event_type": "message_received",
                                "source": "rsu",
                                "current_edge": current_edge,
                                "target_edge": rsu.target_edge,
                                "vehicle_speed_kmph": round(
                                    kmph(traci.vehicle.getSpeed(vehicle_id)), 2
                                ),
                                "limit_kmph": round(kmph(rsu.target_limit_mps), 2),
                            "distance_m": round(distance, 2),
                            "message_id": base_message.message_id,
                            "hops": base_message.hops,
                            "details": "rsu_speed_limit_broadcast",
                        },
                    )

            for sender_id in vehicle_ids:
                sender_memory = memories[sender_id]
                message = best_message_for_vehicle(sender_memory, step)
                if message is None:
                    continue

                if sender_memory.last_forwarded.get(message.target_edge) == step:
                    continue

                sender_x, sender_y = vehicle_positions[sender_id]
                for receiver_id in vehicle_ids:
                    if receiver_id == sender_id:
                        continue

                    receiver_x, receiver_y = vehicle_positions[receiver_id]
                    distance = euclidean(sender_x, sender_y, receiver_x, receiver_y)
                    if distance > config.v2v_range_m:
                        continue

                    forwarded = replace(
                        message,
                        origin_type="vehicle",
                        origin_id=sender_id,
                        ttl_steps=max(message.ttl_steps - 1, 0),
                        hops=message.hops + 1,
                    )
                    if forwarded.ttl_steps <= 0:
                        continue

                    receiver_memory = memories[receiver_id]
                    if accept_message(receiver_memory, forwarded, step):
                        write_event(
                            writer,
                            {
                                "step": step,
                                "vehicle_id": receiver_id,
                                "event_type": "message_received",
                                "source": f"vehicle:{sender_id}",
                                "current_edge": traci.vehicle.getRoadID(receiver_id),
                                "target_edge": forwarded.target_edge,
                                "vehicle_speed_kmph": round(
                                    kmph(traci.vehicle.getSpeed(receiver_id)), 2
                                ),
                                "limit_kmph": round(kmph(forwarded.target_limit_mps), 2),
                                "distance_m": round(distance, 2),
                                "message_id": forwarded.message_id,
                                "hops": forwarded.hops,
                                "details": "v2v_speed_limit_forward",
                            },
                        )

                sender_memory.last_forwarded[message.target_edge] = step

            for sender_id in vehicle_ids:
                lane_id = traci.vehicle.getLaneID(sender_id)
                current_edge = traci.vehicle.getRoadID(sender_id)
                speed_mps = traci.vehicle.getSpeed(sender_id)
                leader_info = traci.vehicle.getLeader(
                    sender_id,
                    max(config.safety_gap_m, config.minimum_follow_distance_m) + 20.0,
                )
                acceleration = traci.vehicle.getAcceleration(sender_id)
                should_broadcast_safety = False
                safety_reason = ""
                recommended_speed_mps = max(speed_mps * 0.7, 4.0)
                risk_distance = None

                if leader_info is not None:
                    _, gap = leader_info
                    if gap <= config.minimum_follow_distance_m:
                        should_broadcast_safety = True
                        safety_reason = "minimum_distance_breach"
                        risk_distance = gap
                        recommended_speed_mps = min(
                            recommended_speed_mps,
                            max(speed_mps * 0.55, 2.5),
                        )
                    if gap <= config.safety_gap_m:
                        should_broadcast_safety = True
                        safety_reason = (
                            f"{safety_reason}+short_headway"
                            if safety_reason else "short_headway"
                        )
                        risk_distance = gap
                        recommended_speed_mps = min(recommended_speed_mps, max(speed_mps * 0.6, 3.0))

                if acceleration <= -config.harsh_brake_threshold_mps2:
                    should_broadcast_safety = True
                    safety_reason = "harsh_brake" if not safety_reason else f"{safety_reason}+harsh_brake"

                if not should_broadcast_safety:
                    continue

                safety_message = SafetyMessage(
                    message_id=f"safety:{sender_id}@{step}",
                    origin_id=sender_id,
                    risk_edge=current_edge,
                    issued_step=step,
                    ttl_steps=8,
                    hops=0,
                    recommended_speed_mps=recommended_speed_mps,
                    reason=safety_reason,
                )

                for receiver_id in vehicle_ids:
                    if receiver_id == sender_id:
                        continue
                    if traci.vehicle.getRoadID(receiver_id) != current_edge:
                        continue
                    sender_x, sender_y = vehicle_positions[sender_id]
                    receiver_x, receiver_y = vehicle_positions[receiver_id]
                    distance = euclidean(sender_x, sender_y, receiver_x, receiver_y)
                    if distance > config.v2v_range_m:
                        continue

                    receiver_memory = memories[receiver_id]
                    if accept_safety_message(receiver_memory, safety_message, step):
                        write_event(
                            writer,
                            {
                                "step": step,
                                "vehicle_id": receiver_id,
                                "event_type": "collision_warning",
                                "source": f"vehicle:{sender_id}",
                                "current_edge": current_edge,
                                "target_edge": current_edge,
                                "vehicle_speed_kmph": round(
                                    kmph(traci.vehicle.getSpeed(receiver_id)), 2
                                ),
                                "limit_kmph": round(
                                    kmph(traci.lane.getMaxSpeed(traci.vehicle.getLaneID(receiver_id))), 2
                                ),
                                "distance_m": round(distance, 2),
                                "message_id": safety_message.message_id,
                                "hops": safety_message.hops,
                                "details": (
                                    f"{safety_reason};recommended={kmph(recommended_speed_mps):.1f}"
                                    + (
                                        f";gap={risk_distance:.1f}"
                                        if risk_distance is not None else ""
                                    )
                                ),
                            },
                        )

            for vehicle_id in vehicle_ids:
                memory = memories[vehicle_id]
                lane_id = traci.vehicle.getLaneID(vehicle_id)
                lane_limit_mps = traci.lane.getMaxSpeed(lane_id)
                current_edge = traci.vehicle.getRoadID(vehicle_id)
                speed_mps = traci.vehicle.getSpeed(vehicle_id)
                lane_pos = traci.vehicle.getLanePosition(vehicle_id)
                lane_length = traci.lane.getLength(lane_id)
                remaining_distance = lane_length - lane_pos

                if speed_mps > lane_limit_mps + 0.5:
                    memory.status = "speeding"
                    if should_emit_alert(memory, "current_limit", step):
                        write_event(
                            writer,
                            {
                                "step": step,
                                "vehicle_id": vehicle_id,
                                "event_type": "current_limit_warning",
                                "source": "controller",
                                "current_edge": current_edge,
                                "target_edge": current_edge,
                                "vehicle_speed_kmph": round(kmph(speed_mps), 2),
                                "limit_kmph": round(kmph(lane_limit_mps), 2),
                                "distance_m": round(remaining_distance, 2),
                                "message_id": "",
                                "hops": "",
                                "details": "current_speed_above_limit",
                            },
                        )

                active_safety = best_safety_message(memory, step)
                if active_safety is not None and current_edge == active_safety.risk_edge:
                    memory.status = "danger"
                    safe_speed = min(
                        active_safety.recommended_speed_mps,
                        lane_limit_mps,
                    )
                    traci.vehicle.slowDown(vehicle_id, safe_speed, 2.5)
                    if should_emit_alert(memory, f"safety:{active_safety.risk_edge}", step, cooldown_steps=3):
                        write_event(
                            writer,
                            {
                                "step": step,
                                "vehicle_id": vehicle_id,
                                "event_type": "collision_response",
                                "source": f"vehicle:{active_safety.origin_id}",
                                "current_edge": current_edge,
                                "target_edge": current_edge,
                                "vehicle_speed_kmph": round(kmph(speed_mps), 2),
                                "limit_kmph": round(kmph(safe_speed), 2),
                                "distance_m": round(remaining_distance, 2),
                                "message_id": active_safety.message_id,
                                "hops": active_safety.hops,
                                "details": active_safety.reason,
                            },
                        )

                active_message = best_message_for_vehicle(memory, step)
                if active_message is None:
                    continue

                if (
                    current_edge == active_message.approach_edge
                    and remaining_distance <= 150.0
                    and speed_mps > active_message.target_limit_mps + 0.5
                    and should_emit_alert(memory, f"upcoming:{active_message.target_edge}", step)
                ):
                    if memory.status not in {"speeding", "danger"}:
                        memory.status = "warned"
                    write_event(
                        writer,
                        {
                            "step": step,
                            "vehicle_id": vehicle_id,
                            "event_type": "upcoming_limit_warning",
                            "source": active_message.origin_type,
                            "current_edge": current_edge,
                            "target_edge": active_message.target_edge,
                            "vehicle_speed_kmph": round(kmph(speed_mps), 2),
                            "limit_kmph": round(kmph(active_message.target_limit_mps), 2),
                            "distance_m": round(remaining_distance, 2),
                            "message_id": active_message.message_id,
                            "hops": active_message.hops,
                            "details": "approaching_lower_speed_zone",
                        },
                    )

            if config.use_gui:
                for vehicle_id in vehicle_ids:
                    update_vehicle_visuals(
                        traci,
                        vehicle_id,
                        memories[vehicle_id],
                        traci.vehicle.getSpeed(vehicle_id),
                    )
                update_vehicle_text_and_table(traci, vehicle_ids, memories)
                update_dashboard_text(traci, step, vehicle_ids, memories, config)
                remove_departed_vehicle_labels(traci, vehicle_ids)

                if vehicle_ids:
                    focus_vehicle = max(
                        vehicle_ids,
                        key=lambda veh_id: (
                            3 if memories[veh_id].status == "danger" else
                            2 if memories[veh_id].status == "speeding" else
                            1 if memories[veh_id].status == "warned" else
                            0,
                            traci.vehicle.getLanePosition(veh_id),
                        ),
                    )
                    focus_speed = kmph(traci.vehicle.getSpeed(focus_vehicle))
                    focus_limit = kmph(
                        traci.lane.getMaxSpeed(traci.vehicle.getLaneID(focus_vehicle))
                    )
                    traci.simulation.writeMessage(
                        f"Focus {focus_vehicle} | speed {focus_speed:.1f} km/h | "
                        f"limit {focus_limit:.0f} km/h | status {memories[focus_vehicle].status.upper()}"
                    )

    traci.close()
    print(f"Simulation complete. Alert log written to: {alert_file}")
    print(f"Runtime route file: {route_file}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a VANET-based speed-limit alert simulation in SUMO."
    )
    parser.add_argument("--gui", action="store_true", help="Launch SUMO with the GUI.")
    parser.add_argument("--delay-ms", type=int, default=600, help="GUI delay per step.")
    parser.add_argument("--vehicle-count", type=int, default=12, help="Number of vehicles.")
    parser.add_argument("--depart-gap", type=int, default=5, help="Seconds between departures.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for vehicle mix.")
    parser.add_argument("--e0-limit", type=int, default=60, help="Speed limit for edge e0.")
    parser.add_argument("--e1-limit", type=int, default=30, help="Speed limit for edge e1.")
    parser.add_argument("--e2-limit", type=int, default=50, help="Speed limit for edge e2.")
    parser.add_argument(
        "--cautious-share",
        type=int,
        default=25,
        help="Share of cautious drivers in percent.",
    )
    parser.add_argument(
        "--aggressive-share",
        type=int,
        default=35,
        help="Share of aggressive drivers in percent.",
    )
    parser.add_argument("--rsu-range", type=int, default=140, help="RSU range in meters.")
    parser.add_argument("--v2v-range", type=int, default=120, help="V2V range in meters.")
    parser.add_argument(
        "--minimum-follow-distance",
        type=int,
        default=18,
        help="Minimum desired distance between vehicles in meters.",
    )
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> SimulationConfig:
    cautious_share = max(0, min(args.cautious_share, 100))
    aggressive_share = max(0, min(args.aggressive_share, 100 - cautious_share))
    return SimulationConfig(
        use_gui=args.gui,
        step_delay_ms=max(args.delay_ms, 0),
        vehicle_count=max(args.vehicle_count, 1),
        depart_gap_s=max(args.depart_gap, 1),
        seed=args.seed,
        e0_limit_kmph=max(args.e0_limit, 10),
        e1_limit_kmph=max(args.e1_limit, 10),
        e2_limit_kmph=max(args.e2_limit, 10),
        cautious_share=cautious_share,
        aggressive_share=aggressive_share,
        rsu_range_m=max(args.rsu_range, 20),
        v2v_range_m=max(args.v2v_range, 20),
        minimum_follow_distance_m=max(args.minimum_follow_distance, 5),
    )


def main() -> int:
    args = parse_args()
    run_simulation(config_from_args(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
