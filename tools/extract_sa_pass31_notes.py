from __future__ import annotations

import json
from pathlib import Path

PASS31_NOTES = {
    "ceiling_laser_crawler": {
        "raw_code": "0x63",
        "object_id": "0x0345",
        "state": "0x21",
        "step_px": 2,
        "timer": "random(20)+30 from special actor table",
        "fire_gate": "active 320x200 viewport + player underneath actor column",
        "projectile": {"bank": 12, "tiles": [44, 45, 46, 47], "dy_px_per_tick": 4},
    },
    "pushable_barrel": {
        "raw_code": "0xA7",
        "bank_tile": "bank6 tile24",
        "blocked_push_behavior": "turn/nudge barrel away from wall; allow player overlap/pass-through for that tick",
    },
    "beam_traps": {
        "raw_codes": ["0x3B", "0x3E"],
        "correction": "end caps static; only middle discharge cel flickers",
        "vertical_tiles": {"static": [27, 26], "middle_idle": 28, "middle_active": [29, 30]},
        "horizontal_tiles": {"static": [32, 33], "middle_idle": 34, "middle_active": [35, 36]},
    },
    "shark_swimmer": {
        "raw_code": "0x5F",
        "bank_tiles": [44, 45, 46, 47],
        "step_px": 2,
        "state_label": "water/swimmer actor; no floor probe",
    },
}

def main() -> int:
    out = Path("docs/derived_mechanics/pass31_mechanics_notes.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(PASS31_NOTES, indent=2), encoding="utf-8")
    print(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
