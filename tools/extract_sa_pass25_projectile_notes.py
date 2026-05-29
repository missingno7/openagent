#!/usr/bin/env python3
"""Emit the pass25 projectile/guard notes recovered from SAM1 disassembly.

This is intentionally small: the relevant facts are direct constants in the
projectile helper and shooter-guard call sites, so keeping them as executable
notes makes future regressions easy to check.
"""
from __future__ import annotations

import json

NOTES = {
    "projectile_helper_entry": "0x5784",
    "object_zero_branch": {
        "writes_object_id": "0x0027",
        "writes_state": "0x0007",
        "writes_frame_counter": 1,
    },
    "player_guard_projectile": {
        "call_object_id": 0,
        "call_speed_px_per_tick": 4,
        "decoded_sprite": {"bank": 1, "right_tile": 38, "left_tile": 39},
    },
    "guard_firing_gate": {
        "row_check": "(player_y + 8) >> 4 == actor_y >> 4",
        "facing_check": True,
        "wall_raycast_before_shooting": False,
    },
    "bank0_actor_0xAE": {
        "right_tile_pairs": [[0, 4], [1, 5], [2, 6], [3, 7]],
        "left_tile_pairs_before_flip": [[4, 0], [5, 1], [6, 2], [7, 3]],
    },
}

if __name__ == "__main__":
    print(json.dumps(NOTES, indent=2))
