#!/usr/bin/env python3
"""Record the EXE-derived animation-timing interpretation used by pass23.

This is intentionally conservative: it does not pretend to fully decompile the
renderer.  It captures the concrete table/state facts we currently rely on and
keeps the implementation traceable to the original EXE fields.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, default=Path("docs/derived_mechanics/pass23_animation_timing.json"))
    args = ap.parse_args()
    root = args.root
    special_path = root / "docs/derived_mechanics/pass18_special_actor_table.json"
    special = json.loads(special_path.read_text(encoding="utf-8"))
    sam1 = {int(r["raw_code"]): r for r in special["SAM1"]}

    data = {
        "rotating_satellite_raw_0x23": {
            "special_actor_table": sam1.get(0x23),
            "correction": "DS:34D8=3 is not the visible graphic frame period. The state 0x20 update at SAM1:0x9785 increments DS:34D6 and wraps it to 1 after 0x13.",
            "implemented_frame_counter": "1..0x13",
            "implemented_visible_mapping": "bank 10 tile = floor((DS:34D6-1)/5), clamped to 0..3",
            "implemented_frames": [[10, 0], [10, 1], [10, 2], [10, 3]],
        },
        "bank4_48_water_or_animated_surface": {
            "raw_code": "0x60",
            "runtime_visual_id": "0x01F3",
            "draw_branch": "SAM1 renderer compares object id 0x01F3 and then tests DS:6840 == 0x10 to choose the paired bitmap.",
            "correction": "The previous 8-tick fallback was visibly too slow. Until DS:6840's full draw-phase schedule is reconstructed, use a faster 4-DOS-tick phase for the 2-frame pair.",
            "implemented_frames": [[4, 48], [4, 0]],
            "implemented_period_ticks": 4,
        },
        "additional_special_actor_table_entries_not_yet_fully_dispatched": [
            r for r in special["SAM1"]
            if int(r["raw_code"]) in {0xAE, 0x56, 0x58, 0x63, 0x24, 0x52, 0x51, 0x3C, 0x3D, 0x40, 0xD4, 0x78}
        ],
    }
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
