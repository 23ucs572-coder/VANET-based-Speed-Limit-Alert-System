from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = ROOT / "scenario"
NODE_FILE = SCENARIO_DIR / "corridor.nod.xml"
EDGE_FILE = SCENARIO_DIR / "corridor.edg.xml"
OUTPUT_FILE = SCENARIO_DIR / "corridor.net.xml"


def main() -> int:
    netconvert = shutil.which("netconvert")
    if netconvert is None:
        print(
            "ERROR: 'netconvert' was not found on PATH. Install SUMO and add it to PATH.",
            file=sys.stderr,
        )
        return 1

    command = [
        netconvert,
        "--node-files",
        str(NODE_FILE),
        "--edge-files",
        str(EDGE_FILE),
        "--output-file",
        str(OUTPUT_FILE),
    ]

    print("Building SUMO network...")
    subprocess.run(command, check=True)
    print(f"Created network: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
