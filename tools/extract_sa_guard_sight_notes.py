#!/usr/bin/env python3
"""Emit the EXE offsets used for the pass15 bank-14 guard sight model.

This is not a full decompiler.  It records the control-flow anchors in the
linear SAM1 disassembly that show row/facing checks before projectile helper
0x5784 is called.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="OpenAgent project root")
    parser.add_argument("--out", default="docs/derived_mechanics/pass15_guard_sight_notes.json")
    args = parser.parse_args()
    root = Path(args.root)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "sam1_guard_sight_branch": {
            "offset_range": "0x63CD..0x6455",
            "actor_y_field": "DS:34D0 + slot*0x20",
            "actor_x_field": "DS:34CE + slot*0x20",
            "actor_direction_field": "DS:34E2 + slot*0x20",
            "actor_timer_field": "DS:34DA + slot*0x20",
            "player_x_field": "DS:34EE",
            "projectile_helper": "0x5784",
            "interpretation": "shoot only when player is on same tile row and in front of actor direction",
        },
        "runtime_model": {
            "line_of_sight": "same row, facing player, no body-solid cell between actor and player",
            "back_shot": "bullet travelling the same direction as guard means it hit from behind; flip DS:34E2 analogue",
        },
    }
    out.write_text(json.dumps(data, indent=2))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
