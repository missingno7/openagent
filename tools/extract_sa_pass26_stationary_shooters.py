#!/usr/bin/env python3
"""Report EXE-derived stationary shooter actors from SAM1.

This complements the special actor table extractor by documenting the update
branch around SAM1:0x6B74..0x6D47 where states 0x0A..0x0D fire projectiles
only when the player is on the same 16px row and in front of the emitter.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from openagent.exe_actor_mechanics import (  # noqa: E402
    SPECIAL_ACTOR_MODELS,
    STATIONARY_SHOOTER_DIRECTION,
    STATIONARY_SHOOTER_PROJECTILE,
    STATIONARY_SHOOTER_SPAWN_X_OFFSET,
)

CODES = (0x52, 0x51, 0x3C, 0x3D)

# Decoded from the helper calls in the dispatcher, not guessed from the atlas.
PROJECTILE_OBJECT_BY_CODE = {
    0x52: "0x01D6",
    0x51: "0x01D6",
    0x3C: "0x01E8",
    0x3D: "0x01EC",
}


def record(code: int):
    m = SPECIAL_ACTOR_MODELS[code]
    bank, tr, tl = STATIONARY_SHOOTER_PROJECTILE[code]
    return {
        "raw_code_hex": f"0x{code:02X}",
        "object_id_hex": f"0x{m.object_id:04X}",
        "behavior_state_hex": f"0x{m.behavior_state:02X}",
        "direction": "right" if STATIONARY_SHOOTER_DIRECTION[code] > 0 else "left",
        "timer": "random(20)+55 ticks",
        "timer_min": m.timer_min,
        "timer_max": m.timer_max,
        "fires_when": "(player_y+8)&0xFFF0 == actor_y&0xFFF0 and player is in front",
        "projectile_object_id_hex": PROJECTILE_OBJECT_BY_CODE[code],
        "projectile_speed_px_per_tick": 4,
        "projectile_bank": bank,
        "projectile_tile_right": tr,
        "projectile_tile_left": tl,
        "projectile_x_offset": STATIONARY_SHOOTER_SPAWN_X_OFFSET[code],
    }


def main() -> int:
    out_dir = ROOT / "docs" / "derived_mechanics"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {f"0x{code:02X}": record(code) for code in CODES}
    path = out_dir / "pass26_stationary_shooter_mechanics.json"
    path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {path}")
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
