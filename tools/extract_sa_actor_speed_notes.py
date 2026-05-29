#!/usr/bin/env python3
"""Small research note generator for actor speed constants.

This does not try to recover the full actor dispatch table yet.  It records the
field-level mechanism observed in the disassembly: DS:34E6 + slot*0x20 is the
per-tick pixel step and common branches write small constants 1, 2 and 3.
"""
from __future__ import annotations

import json
from pathlib import Path

NOTES = {
    "field": "DS:34E6 + slot*0x20",
    "unit": "pixels per DOS game tick",
    "sam1_offsets": {
        "0x5EF8": "mov word [34E6+slot], 1",
        "0x617F": "mov word [34E6+slot], 2",
        "0x64D6": "mov word [34E6+slot], 3",
    },
    "runtime_mapping_pass17": {
        "0x62_moving_platform": {"step_px": 1, "initial_direction": -1},
        "0x65": {"step_px": 1},
        "0x75": {"step_px": 1},
        "0x76": {"step_px": 1},
        "0x6E": {"step_px": 2},
        "bank14_guards": {"step_px": 1},
    },
}


def main() -> int:
    out = Path("docs/derived_mechanics/pass17_actor_speed_notes.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(NOTES, indent=2) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
