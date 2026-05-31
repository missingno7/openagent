#!/usr/bin/env python3
"""Regression checks for ASM death-arc camera and platform catch behaviour."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.entities import LevelEntities, MovingPlatform
from openagent.game_constants import PLAYER_VERTICAL_COUNTER_INITIAL
from openagent.player import Player
from openagent.runtime import OpenAgentApp


class DeathProbe:
    is_world_map = False
    visual_interpolation_enabled = False

    def __init__(self) -> None:
        self.player = Player(64, 300)
        self.player_dead_timer = 2
        self.player_death_frame_counter = 0
        self._death_camera = (0, 100)
        self._force_next_draw = False
        self.respawned = False

    update_player_death_tick = OpenAgentApp.update_player_death_tick
    camera = OpenAgentApp.camera

    def respawn_after_death(self) -> None:
        self.respawned = True


class PlatformProbe:
    def __init__(self, *, dead: bool) -> None:
        platform = MovingPlatform(64.0, 80.0, direction=1, step_px=2)
        self.platform = platform
        self.entities = LevelEntities([platform], [], [], [], [], [], [], [], [])
        self.player = Player(64, 64)
        self.player.grounded = not dead
        self.player_dead_timer = 1 if dead else 0

    update_entities_tick = OpenAgentApp.update_entities_tick
    platform_carry_contact_asm = OpenAgentApp.platform_carry_contact_asm

    def platform_collides(self, platform) -> bool:
        return False

    def update_barrels_tick(self) -> None:
        pass

    def update_projectiles_tick(self) -> None:
        pass


def main() -> int:
    death = DeathProbe()
    assert death.camera() == (0, 100), "death camera must stay frozen"
    death.update_player_death_tick()
    assert death.player.y == 100 + 0xB8, death.player.y
    assert not death.respawned

    alive = PlatformProbe(dead=False)
    assert alive.platform_carry_contact_asm(alive.platform)
    alive.update_entities_tick()
    assert alive.platform.x == 66.0
    assert alive.player.x == 66.0, "normal platform carry should remain active"
    assert alive.player.y == 64.0
    assert alive.player.fall_ticks == PLAYER_VERTICAL_COUNTER_INITIAL

    dead = PlatformProbe(dead=True)
    assert dead.platform_carry_contact_asm(dead.platform)
    dead.update_entities_tick()
    assert dead.platform.x == 66.0
    assert dead.player.x == 66.0, "DS:69F5 does not disable platform carry in ASM"
    assert dead.player.y == 64.0, "platform branch snaps death sprite to actor_y-0x10"
    assert dead.player.grounded

    miss = PlatformProbe(dead=True)
    miss.player.y = 40.0
    assert not miss.platform_carry_contact_asm(miss.platform)

    print("death camera/platform catch smoke OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
