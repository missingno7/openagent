#!/usr/bin/env python3
"""Emit a small coverage report for currently decoded Secret Agent special actors.

This is deliberately data-first: it reads the EXE-derived special actor table
from pass18 and marks which raw codes are already promoted to runtime entities.
"""
from __future__ import annotations

import json
from pathlib import Path

IMPLEMENTED = {
    0x23: "rotating satellite actor, bank10 0..3, 3-tick period",
    0x3B: "vertical timed bank3 beam trap, state 0x0F",
    0x3E: "horizontal timed bank3 beam trap, state 0x10",
    0x3F: "floor spike trap, state 0x11",
    0x41: "ceiling spike trap, state 0x12",
    0x38: "bank14 guard tier 0",
    0x39: "bank14 guard tier 8",
    0x30: "bank14 guard tier 16",
    0x67: "bank14 shooter guard tier 24",
    0x47: "bank14 shooter guard tier 32",
    0x52: "stationary shooter right, projectile 0x01D6",
    0x51: "stationary shooter left, projectile 0x01D6",
    0x3C: "stationary shooter right, projectile 0x01E8",
    0x3D: "stationary shooter left, projectile 0x01EC",
    0x65: "simple walker, bank2 16..23",
    0x6E: "mirrored simple walker, bank2 32..35",
    0x7F: "mirrored simple walker, bank5 8..11",
    0xAE: "two-wide bank0 walker",
    0x24: "two-high bank2 helmet actor, first-pass synchronized animation",
    0x56: "bank12 two-high actor, first-pass walker",
    0x58: "bank12 two-high actor, first-pass walker",
    0x63: "bank12 one-tile actor, first-pass walker",
}

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "docs" / "derived_mechanics" / "pass18_special_actor_table.json"
out = ROOT / "docs" / "derived_mechanics" / "pass27_actor_gap_report.json"

data = json.loads(source.read_text())
rows = data["SAM1"]
report = []
for row in rows:
    code = int(row["raw_code"])
    report.append({
        "raw_code_hex": f"0x{code:02X}",
        "object_id_hex": row["object_id_hex"],
        "behavior_state_hex": f"0x{int(row['behavior_state']):02X}" if row.get("behavior_state") is not None else None,
        "step_px": row.get("step_px"),
        "timer_period": row.get("timer_period"),
        "timer_period_random": row.get("timer_period_random"),
        "implemented": code in IMPLEMENTED,
        "runtime_note": IMPLEMENTED.get(code, "not yet promoted or still needs state-specific dispatcher"),
    })

out.write_text(json.dumps(report, indent=2))
print(f"wrote {out}")
for item in report:
    status = "OK " if item["implemented"] else "TODO"
    print(f"{status} {item['raw_code_hex']} state={item['behavior_state_hex']} obj={item['object_id_hex']} {item['runtime_note']}")
