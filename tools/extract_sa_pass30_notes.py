#!/usr/bin/env python3
"""Emit the pass30 actor notes in machine-readable form.

This is intentionally a small report over already extracted special-actor facts.
It keeps the ceiling-laser/barrel pass reproducible from the checked-in notes.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

report = {
    "bank12_ceiling_laser": {
        "raw_code": "0x63",
        "object_id": "0x0345",
        "state": "0x21",
        "speed_px_per_tick": 2,
        "timer": "random(20)+30",
        "bank_tiles": "bank12 36..43",
    },
    "pushable_barrel": {
        "raw_code": "0xA7",
        "bank_tile": "bank6 tile24",
    },
}

out = ROOT / "docs" / "derived_mechanics" / "pass30_ceiling_laser_barrel.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(out)
