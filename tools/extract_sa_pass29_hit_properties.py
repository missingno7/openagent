#!/usr/bin/env python3
"""Document actor hit/durability properties recovered from SAM EXE branches.

This is intentionally conservative: it records the currently understood EXE
object-id gates instead of turning every actor slot into a damageable enemy.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.exe_actor_mechanics import (  # noqa: E402
    SPECIAL_ACTOR_MODELS,
    SHOOTABLE_OBJECT_ID_RANGES,
    SHOOTABLE_OBJECT_IDS,
    STATIONARY_SHOOTER_DIRECTION,
    STATIONARY_SHOOTER_PROJECTILE,
    ACTOR_HP_BY_OBJECT_ID,
)
from openagent.semantics import STATIONARY_SHOOTER_CODES, BANK14_GUARD_CODES  # noqa: E402


def classify_object_id(object_id: int) -> str:
    if object_id in SHOOTABLE_OBJECT_IDS:
        return "shootable_object_branch"
    if any(lo <= object_id <= hi for lo, hi in SHOOTABLE_OBJECT_ID_RANGES):
        return "shootable_range_branch"
    return "no_known_player_shot_damage_branch"


def main() -> int:
    rows = []
    for raw, model in sorted(SPECIAL_ACTOR_MODELS.items()):
        kind = "bank14_guard" if raw in BANK14_GUARD_CODES else "stationary_shooter" if raw in STATIONARY_SHOOTER_CODES else "actor"
        rows.append({
            "raw_code": f"0x{raw:02X}",
            "object_id": f"0x{model.object_id:04X}",
            "state": f"0x{model.behavior_state:02X}",
            "kind": kind,
            "shot_damage_class": classify_object_id(model.object_id),
            "hp_hint": ACTOR_HP_BY_OBJECT_ID.get(model.object_id, model.aux_dc),
            "stationary_direction": STATIONARY_SHOOTER_DIRECTION.get(raw),
            "stationary_projectile": STATIONARY_SHOOTER_PROJECTILE.get(raw),
        })
    out = {
        "evidence": {
            "hit_dispatcher": "SAM1 0x4BD2..0x4ED5 branches on actor object id DS:34E0",
            "projectile_impact": "SAM1 0x4F15 and 0x5C59 convert projectile slot to impact/boom state",
            "stationary_shooters": "object ids 0x01D0/0x01D1/0x01E7/0x01EB are not in the decoded shot-damage branches",
            "impact_sprite": "decoded visible impact family is bank 5 tiles 24..27",
        },
        "shootable_object_ids": [f"0x{x:04X}" for x in sorted(SHOOTABLE_OBJECT_IDS)],
        "shootable_object_id_ranges": [[f"0x{lo:04X}", f"0x{hi:04X}"] for lo, hi in SHOOTABLE_OBJECT_ID_RANGES],
        "actors": rows,
    }
    out_path = ROOT / "docs" / "derived_mechanics" / "pass29_hit_properties.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
