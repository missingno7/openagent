from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "derived_mechanics" / "pass21_spike_traps.json"

DATA = {
    "source": "Manual extraction from SAM1_unpacked_linear_8086.asm actor init/update branches.",
    "floor_spike": {
        "raw_code": "0x3F",
        "init_branch": "SAM1 0x13A75",
        "update_branch": "SAM1 0x6FBB..0x7041",
        "state": "0x11",
        "idle_object_id": "0x01B3",
        "period_ticks": 0x1E,
        "cycle_ticks": 0x3C,
        "initial_timer": "random(0x1E)",
        "visual_base_id": "0x01D7",
        "bank": 4,
        "tiles": list(range(20, 28)),
        "draw_y_offset": 8,
    },
    "ceiling_spike": {
        "raw_code": "0x41",
        "init_branch": "SAM1 0x13B9B",
        "update_branch": "SAM1 0x704C..0x70D2",
        "state": "0x12",
        "idle_object_id": "0x01B3",
        "period_ticks": 0x1E,
        "cycle_ticks": 0x3C,
        "initial_timer": "random(0x1E)",
        "visual_base_id": "0x01DF",
        "bank": 4,
        "tiles": list(range(28, 36)),
        "draw_y_offset": -8,
    },
}

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(DATA, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
