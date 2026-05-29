#!/usr/bin/env python3
"""Emit the pass24 actor/projectile findings in a small stable JSON file.

This is intentionally a report wrapper around the EXE-derived table data that
has already been extracted into openagent.exe_actor_mechanics.  It makes the
newly implemented entries easy to diff without re-reading the whole disassembly.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from openagent.exe_actor_mechanics import SPECIAL_ACTOR_MODELS  # noqa: E402

INTERESTING = [0x23, 0x62, 0xAE, 0x24, 0x56, 0x58, 0x63]

def model_dict(code: int):
    m = SPECIAL_ACTOR_MODELS.get(code)
    if not m:
        return None
    return {
        "raw_code_hex": f"0x{code:02X}",
        "object_id_hex": f"0x{m.object_id:04X}",
        "step_px": m.step_px,
        "behavior_state_hex": f"0x{m.behavior_state:02X}",
        "timer_min": m.timer_min,
        "timer_max": m.timer_max,
        "aux_dc": m.aux_dc,
        "random_initial_direction": m.random_initial_direction,
    }


def main() -> int:
    out = {f"0x{c:02X}": model_dict(c) for c in INTERESTING if model_dict(c) is not None}
    out["0x62"] = {"note": "moving platform raw token; not part of the current special actor table extractor; runtime now uses 2 px/tick, start left"}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
