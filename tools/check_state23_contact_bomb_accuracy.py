#!/usr/bin/env python3
"""Regression checks for raw 0x75 / state 0x23 actor behaviour.

ASM evidence:
  * SAM1:0x127C6..0x1288C initializes raw 0x75 as object 0x006D,
    DS:34E2=+1, DS:34E6=0, DS:34DC=3, DS:34E8=0x23.
  * SAM1:0x9FED..0xA15E advances the frame counter, calls helper 0x53C4
    for player contact damage, then helper 0x547C for projectile/actor hits.
    Only the 0x547C path decrements DS:34DC and eventually awards 1000 points.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.animation import state23_contact_bomb_tile
from openagent.entities import Enemy, LevelEntities, Projectile
from openagent.exe_actor_mechanics import (
    STATE23_CONTACT_BOMB_CODE,
    STATE23_CONTACT_BOMB_SCORE,
    STATE23_SHRAPNEL_LEFT_TILE,
    STATE23_SHRAPNEL_RIGHT_TILE,
)
from openagent.game_assets.constants import TILE
from openagent.player import Player
from openagent.runtime import OpenAgentApp


class State23RuntimeProbe(OpenAgentApp):
    def __init__(self, enemy: Enemy) -> None:
        self.player = Player(x=enemy.x, y=enemy.y)
        self.entities = LevelEntities([], [enemy], [], [], [], [], [], [], [])
        self.hurt_flash = 0.0
        self.hurt_calls = 0
        self.score = 0
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


def make_state23_enemy(*, x: float = 64.0, y: float = 64.0) -> Enemy:
    return Enemy(
        x,
        y,
        code=STATE23_CONTACT_BOMB_CODE,
        direction=1,
        step_px=0,
        frame_counter=1,
        kind="state23_contact_bomb",
        behavior_state=0x23,
        object_id=0x006D,
        hp=3,
    )


def check_state23_contact_hurts_but_does_not_move_or_explode() -> None:
    enemy = make_state23_enemy()
    probe = State23RuntimeProbe(enemy)
    start = (enemy.x, enemy.y)

    OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert (enemy.x, enemy.y) == start
    assert enemy.step_px == 0
    assert enemy.frame_counter == 2
    assert probe.hurt_calls == 1
    assert enemy in probe.entities.enemies
    assert enemy.hp == 3
    assert probe.score == 0
    assert len(probe.entities.projectiles) == 0


def check_repeated_player_contact_never_counts_down_damage_hp() -> None:
    enemy = make_state23_enemy()
    probe = State23RuntimeProbe(enemy)

    for _ in range(5):
        probe.hurt_flash = 0.0
        OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert probe.hurt_calls == 5
    assert enemy in probe.entities.enemies
    assert enemy.hp == 3
    assert probe.score == 0
    assert len(probe.entities.projectiles) == 0


def check_projectile_hits_count_down_and_final_hit_explodes() -> None:
    enemy = make_state23_enemy()
    probe = State23RuntimeProbe(enemy)
    shot = Projectile(enemy.x - 4, enemy.y + 8, 1, hostile=False, owner="player")

    OpenAgentApp.hit_enemy_with_projectile(probe, enemy, shot)  # type: ignore[arg-type]
    assert enemy in probe.entities.enemies
    assert enemy.hp == 2
    assert enemy.hit_flash_ticks == 3
    assert probe.score == 0

    OpenAgentApp.hit_enemy_with_projectile(probe, enemy, shot)  # type: ignore[arg-type]
    assert enemy in probe.entities.enemies
    assert enemy.hp == 1
    assert probe.score == 0

    OpenAgentApp.hit_enemy_with_projectile(probe, enemy, shot)  # type: ignore[arg-type]
    assert enemy not in probe.entities.enemies
    assert probe.score == STATE23_CONTACT_BOMB_SCORE
    assert len(probe.entities.projectiles) == 2
    directions = sorted(shot.direction for shot in probe.entities.projectiles)
    assert directions == [-1, 1]
    tiles = {(shot.tile_right, shot.tile_left) for shot in probe.entities.projectiles}
    assert tiles == {(STATE23_SHRAPNEL_RIGHT_TILE, STATE23_SHRAPNEL_LEFT_TILE)}


def check_state23_animation_range_and_wrap() -> None:
    assert state23_contact_bomb_tile(1) == (2, 8)
    assert state23_contact_bomb_tile(5) == (2, 8)
    assert state23_contact_bomb_tile(6) == (2, 9)
    assert state23_contact_bomb_tile(11) == (2, 10)
    assert state23_contact_bomb_tile(16) == (2, 11)

    enemy = make_state23_enemy()
    enemy.frame_counter = 0x13
    probe = State23RuntimeProbe(enemy)
    probe.player.x = enemy.x + 64  # no contact, only tick the state.

    OpenAgentApp.update_entities_tick(probe)  # type: ignore[arg-type]

    assert enemy.frame_counter == 1
    assert probe.hurt_calls == 0


def main() -> int:
    check_state23_contact_hurts_but_does_not_move_or_explode()
    check_repeated_player_contact_never_counts_down_damage_hp()
    check_projectile_hits_count_down_and_final_hit_explodes()
    check_state23_animation_range_and_wrap()
    print("state23 contact bomb accuracy checks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
