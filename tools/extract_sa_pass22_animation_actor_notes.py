#!/usr/bin/env python3
"""Summarise the EXE-derived notes used in pass22.

This does not attempt a full disassembly. It combines the already extracted
special actor table (CS:3A59) with the current decoded atlas mapping, so the
runtime changes stay traceable to game data rather than visual guesses.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, default=Path("docs/derived_mechanics/pass22_spikes_satellite_actor_notes.json"))
    args = ap.parse_args()
    root = args.root
    table_path = root / "docs/derived_mechanics/pass18_special_actor_table.json"
    table = json.loads(table_path.read_text())
    sam1 = {int(rec["raw_code"]): rec for rec in table["SAM1"]}

    notes = {
        "spike_position_correction": {
            "raw_codes": {"floor": "0x3F", "ceiling": "0x41"},
            "reason": "The previous decoded-coordinate renderer applied the EXE half-tile sprite-origin offset a second time. Draw origins are corrected up by 8 pixels: floor spikes draw at the map-cell Y, ceiling spikes at Y-16.",
            "bank4_floor_tiles": "20..27",
            "bank4_ceiling_tiles": "28..35",
        },
        "rotating_satellite": {
            "raw_code": "0x23",
            "special_actor_table": sam1.get(0x23),
            "decoded_tile_family": "bank 10 tiles 0..3",
            "implemented_frames": [[10, 0], [10, 1], [10, 2], [10, 3]],
            "period_ticks": 3,
        },
        "bank2_6e_actor": {
            "raw_code": "0x6E",
            "special_actor_table": sam1.get(0x6E),
            "correction": "Use bank 2 tiles 32..35 only. Tiles 36..39 are a different blue actor family, not the left-facing half of 0x6E. Left motion is mirrored at draw time.",
        },
        "bank5_7f_actor": {
            "raw_code": "0x7F",
            "special_actor_table": sam1.get(0x7F),
            "decoded_tile_family": "bank 5 tiles 8..11",
            "implemented_step_px": 2,
            "implemented_timer_period": 2,
            "draw_note": "Single 4-frame family mirrored for left movement.",
        },
    }
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(notes, indent=2), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
