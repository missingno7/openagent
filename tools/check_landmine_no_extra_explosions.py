#!/usr/bin/env python3
"""Regression smoke test for raw 0x4D triggered mine explosion fan-out.

ASM state 0x17/object 0x0271 draws/clears the mine blast through direct render
helpers. It must not allocate three additional persistent projectile-impact
Explosion entities in the runtime model.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.entities import Enemy, LevelEntities
from openagent.exe_actor_mechanics import STATE17_LANDMINE_DAMAGE_FRAME, STATE17_LANDMINE_TRIGGERED_OBJECT_ID
from openagent.runtime import OpenAgentApp


class LandmineProbe:
    def __init__(self) -> None:
        self.entities = LevelEntities([], [], [], [], [], [], [], [], [])
        self.entities.enemies.append(
            Enemy(
                64,
                64,
                code=0x4D,
                kind="state17_landmine",
                object_id=STATE17_LANDMINE_TRIGGERED_OBJECT_ID,
                frame_counter=STATE17_LANDMINE_DAMAGE_FRAME,
            )
        )
        self.hurt_flash = 0.0
        self.spawn_calls = 0

    def enemy_overlaps_player(self, enemy: Enemy) -> bool:
        return False

    def kill_player(self) -> None:
        raise AssertionError("triggered mine should not kill in this test when overlap is false")

    def spawn_projectile_explosion(self, x: float, y: float) -> None:
        self.spawn_calls += 1
        raise AssertionError("triggered mine must not spawn persistent extra Explosion entities")

    def update_barrels_tick(self) -> None:
        pass

    def update_projectiles_tick(self) -> None:
        pass


def main() -> int:
    probe = LandmineProbe()
    OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]
    mine = probe.entities.enemies[0]
    assert mine.frame_counter == STATE17_LANDMINE_DAMAGE_FRAME + 1
    assert probe.spawn_calls == 0
    assert probe.entities.explosions == []
    print("Landmine no-extra-explosions smoke OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
