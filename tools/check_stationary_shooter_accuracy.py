#!/usr/bin/env python3
"""Regression checks for the stationary launcher actor family.

SAM1 states 0x0A/0x0B/0x0C/0x0D keep DS:34DA as an elapsed timer.  The timer
increments regardless of whether the player is currently in the same row; once
charged it is reset only after the row+front gate succeeds and helper 0x5784
spawns the projectile.  Raw 0x51/0x52 bodies are not decoded as solid/contact
hazards: they are hostile through their projectile only.  Pass 129 also checks
that 0x01D6 shots and 0x01E8/0x01EC rockets hurt but pass through the player.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.entities import Enemy, LevelEntities
from openagent.exe_actor_mechanics import SPECIAL_ACTOR_MODELS, STATIONARY_SHOOTER_DIRECTION
from openagent.game_assets.constants import TILE
from openagent.movement_collision import MovementCollisionMixin
from openagent.player import Player
from openagent.runtime import OpenAgentApp


class StationaryRuntimeProbe(OpenAgentApp):
    def __init__(self, enemy: Enemy) -> None:
        self.player = Player(x=enemy.x + 32, y=enemy.y)
        self.entities = LevelEntities([], [enemy], [], [], [], [], [], [], [])
        self.hurt_flash = 0.0
        self.hurt_calls = 0
        self.sound_calls: list[int] = []

    def active_camera(self) -> tuple[int, int]:
        return (0, 0)

    def rect_in_active_viewport(self, x: float, y: float, w: int = TILE, h: int = TILE, margin: int = 0) -> bool:
        return True

    def play_sound(self, sound_id: int) -> None:
        self.sound_calls.append(sound_id)

    def hurt_player(self) -> None:
        self.hurt_calls += 1
        self.hurt_flash = 1.0

    def kill_player(self) -> None:
        self.hurt_calls += 1
        self.hurt_flash = 1.0

    def cell_blocks_body(self, x: int, y: int) -> bool:
        return False

    def cell_solid(self, x: int, y: int) -> bool:
        return False

    def platform_carry_contact_asm(self, platform) -> bool:
        return False

    def platform_collides(self, platform) -> bool:
        return False

    def update_barrels_tick(self) -> None:
        return None

    def update_projectiles_tick(self) -> None:
        return None


class StationaryCollisionProbe(MovementCollisionMixin):
    def __init__(self, enemy: Enemy) -> None:
        self.player = Player(x=enemy.x - TILE + 3, y=enemy.y)
        self.entities = type("Entities", (), {"enemies": [enemy], "barrels": []})()
        self.collision_enabled = True
        self._ignore_barrel_collision = None
        self._ignore_barrel_collision_ticks = 0
        self.hurt_flash = 0.0
        self.hurt_calls = 0

    def cell_blocks_body(self, x: int, y: int) -> bool:
        return False

    def cell_solid(self, x: int, y: int) -> bool:
        return False

    def actor_is_indestructible_solid(self, enemy: Enemy) -> bool:
        return OpenAgentApp.actor_is_indestructible_solid(self, enemy)  # type: ignore[arg-type]

    def actor_is_contact_hazard(self, enemy: Enemy) -> bool:
        return OpenAgentApp.actor_is_contact_hazard(self, enemy)  # type: ignore[arg-type]

    def actor_rect(self, enemy: Enemy) -> tuple[float, float, float, float]:
        return OpenAgentApp.actor_rect(self, enemy)  # type: ignore[arg-type]

    def actor_contains_point(self, enemy: Enemy, x: float, y: float) -> bool:
        return OpenAgentApp.actor_contains_point(self, enemy, x, y)  # type: ignore[arg-type]

    def hurt_player(self) -> None:
        self.hurt_calls += 1
        self.hurt_flash = 1.0


def make_stationary(code: int, *, x: float = 64.0, y: float = 64.0, timer: int = 3) -> Enemy:
    model = SPECIAL_ACTOR_MODELS[code]
    direction = STATIONARY_SHOOTER_DIRECTION[code]
    return Enemy(
        x,
        y,
        code=code,
        direction=direction,
        step_px=0,
        shoot_interval_ticks=timer,
        shoot_timer_ticks=0,
        kind="stationary_shooter",
        behavior_state=model.behavior_state,
        object_id=model.object_id,
        hp=0,
    )


def check_elapsed_timer_charges_before_line_of_sight() -> None:
    enemy = make_stationary(0x52, timer=3)
    probe = StationaryRuntimeProbe(enemy)
    probe.player.y = enemy.y + 32  # not the same tile row; launcher should charge but not fire.

    for _ in range(5):
        OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert enemy.shoot_timer_ticks == 3, enemy.shoot_timer_ticks
    assert len(probe.entities.projectiles) == 0

    probe.player.y = enemy.y
    OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert enemy.shoot_timer_ticks == 0, enemy.shoot_timer_ticks
    assert len(probe.entities.projectiles) == 1
    shot = probe.entities.projectiles[0]
    assert shot.x == enemy.x + 8
    # ASM helper receives actor_y.  This runtime renders horizontal projectile
    # sprites at y-7, so the stored logical y is actor_y+7 to display at actor_y.
    assert shot.y == enemy.y + 7
    assert shot.direction == 1
    assert shot.bank == 4 and shot.tile_right == 19 and shot.tile_left == 19


def check_left_facing_launcher_uses_negative_gate_and_offset() -> None:
    enemy = make_stationary(0x51, x=64.0, y=64.0, timer=1)
    probe = StationaryRuntimeProbe(enemy)
    probe.player.x = enemy.x - 32
    probe.player.y = enemy.y

    OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert len(probe.entities.projectiles) == 1
    shot = probe.entities.projectiles[0]
    assert shot.x == enemy.x - 8
    assert shot.y == enemy.y + 7
    assert shot.direction == -1




def check_right_rocket_launcher_uses_state0e_spawn_and_passes_through_player() -> None:
    enemy = make_stationary(0x3C, x=64.0, y=64.0, timer=1)
    probe = StationaryRuntimeProbe(enemy)
    probe.player.x = enemy.x + 32
    probe.player.y = enemy.y

    OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert len(probe.entities.projectiles) == 1
    shot = probe.entities.projectiles[0]
    assert shot.x == enemy.x + 16
    assert shot.y == enemy.y + 7
    assert shot.direction == 1
    assert shot.bank == 4 and shot.tile_right == 37 and shot.tile_left == 41
    assert shot.keep_on_player_hit
    assert shot.narrow_hurt_on_hit
    assert shot.hit_y_offset == -7

    old_x = shot.x
    probe.player.x = shot.x + 4
    probe.player.y = enemy.y
    OpenAgentApp.update_projectiles_tick(probe)  # type: ignore[arg-type]

    assert probe.hurt_calls == 1
    assert len(probe.entities.projectiles) == 1
    assert not probe.entities.projectiles[0].is_impact
    assert probe.entities.projectiles[0].x == old_x + 4


def check_left_rocket_launcher_uses_negative_offset_and_passes_through_player() -> None:
    enemy = make_stationary(0x3D, x=80.0, y=64.0, timer=1)
    probe = StationaryRuntimeProbe(enemy)
    probe.player.x = enemy.x - 32
    probe.player.y = enemy.y

    OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert len(probe.entities.projectiles) == 1
    shot = probe.entities.projectiles[0]
    assert shot.x == enemy.x - 16
    assert shot.y == enemy.y + 7
    assert shot.direction == -1
    assert shot.bank == 4 and shot.tile_right == 37 and shot.tile_left == 41

    old_x = shot.x
    probe.player.x = shot.x - 4
    probe.player.y = enemy.y
    OpenAgentApp.update_projectiles_tick(probe)  # type: ignore[arg-type]

    assert probe.hurt_calls == 1
    assert len(probe.entities.projectiles) == 1
    assert not probe.entities.projectiles[0].is_impact
    assert probe.entities.projectiles[0].x == old_x - 4


def check_0x51_0x52_projectile_passes_through_player_after_hurt() -> None:
    enemy = make_stationary(0x52, x=64.0, y=64.0, timer=1)
    probe = StationaryRuntimeProbe(enemy)
    probe.player.x = enemy.x + 32
    probe.player.y = enemy.y

    OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert len(probe.entities.projectiles) == 1
    shot = probe.entities.projectiles[0]
    assert shot.keep_on_player_hit
    assert shot.narrow_hurt_on_hit
    old_x = shot.x
    probe.player.x = shot.x + 4
    probe.player.y = enemy.y

    OpenAgentApp.update_projectiles_tick(probe)  # type: ignore[arg-type]

    assert probe.hurt_calls == 1
    assert len(probe.entities.projectiles) == 1
    assert not probe.entities.projectiles[0].is_impact
    assert probe.entities.projectiles[0].x == old_x + 4

def check_body_contact_is_harmless() -> None:
    enemy = make_stationary(0x52)
    probe = StationaryRuntimeProbe(enemy)
    probe.player.x = enemy.x
    probe.player.y = enemy.y

    OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert probe.hurt_calls == 0


def check_global_enemy_touch_pass_does_not_hurt_stationary_launcher() -> None:
    enemy = make_stationary(0x52)
    probe = StationaryRuntimeProbe(enemy)
    probe.player.x = enemy.x
    probe.player.y = enemy.y

    # Pass 120 fixed the dynamic actor-body helpers, but the later generic
    # check_enemy_touch() fallback could still damage the player unless raw
    # 0x51/0x52 are explicitly excluded from broad body contact.
    OpenAgentApp.check_enemy_touch(probe, 1.0 / 18.2)  # type: ignore[arg-type]

    assert probe.hurt_calls == 0
    assert probe.hurt_flash == 0.0


def check_actor_body_does_not_block_player_movement() -> None:
    enemy = make_stationary(0x52, x=64.0, y=64.0)
    probe = StationaryCollisionProbe(enemy)
    start_x = probe.player.x
    blocked = probe.move_player_horizontal_tick(1)

    assert not OpenAgentApp.actor_is_indestructible_solid(probe, enemy)  # type: ignore[arg-type]
    assert not OpenAgentApp.actor_is_contact_hazard(probe, enemy)  # type: ignore[arg-type]
    assert not blocked
    assert probe.player.x == start_x + 1
    assert probe.hurt_calls == 0


def main() -> int:
    check_elapsed_timer_charges_before_line_of_sight()
    check_left_facing_launcher_uses_negative_gate_and_offset()
    check_right_rocket_launcher_uses_state0e_spawn_and_passes_through_player()
    check_left_rocket_launcher_uses_negative_offset_and_passes_through_player()
    check_0x51_0x52_projectile_passes_through_player_after_hurt()
    check_body_contact_is_harmless()
    check_global_enemy_touch_pass_does_not_hurt_stationary_launcher()
    check_actor_body_does_not_block_player_movement()
    print("stationary shooter accuracy checks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
