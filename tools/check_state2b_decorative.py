#!/usr/bin/env python3
"""Regression smoke test for raw 0x40 / object 0x0131 / state 0x2B.

ASM state 0x2B only advances the animation timer; unlike state 0x2C object
0x0103, it does not call helper 0x53C4.  The runtime must therefore render it as
an animated decorative two-cell object and must not route broad enemy-body
contact into player damage.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.animation import state2b_actor_refs
from openagent.entities import Enemy, LevelEntities
from openagent.player import Player
from openagent.runtime import OpenAgentApp


class State2BProbe:
    def __init__(self) -> None:
        self.player = Player(x=64, y=64)
        self.entities = LevelEntities([], [], [], [], [], [], [], [], [])
        self.entities.enemies.append(
            Enemy(
                64,
                64,
                code=0x40,
                kind="state2b_anim",
                object_id=0x0131,
                behavior_state=0x2B,
                frame_counter=1,
            )
        )
        self.hurt_flash = 0.0
        self.hurt_calls = 0

    def hurt_player(self) -> None:
        self.hurt_calls += 1


def main() -> int:
    refs = state2b_actor_refs(1)
    assert refs[0] == (0, -1, 9, 4), f"unexpected state2B top cel: {refs[0]}"
    assert refs[1] == (0, 0, 9, 1), f"state2B lower cel must be bank9:1, got {refs[1]}"

    probe = State2BProbe()
    OpenAgentApp.check_enemy_touch(probe, 1 / 18.2)  # type: ignore[arg-type]
    assert probe.hurt_calls == 0, "raw 0x40/state 0x2B must not hurt on broad body overlap"
    assert probe.hurt_flash == 0.0
    print("State2B decorative/non-contact smoke OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
