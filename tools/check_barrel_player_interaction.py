#!/usr/bin/env python3
"""Regression checks for raw 0xA7 player/barrel contact geometry.

SAM1:0x83C4..0x848A does not use full 16x16 sprite AABBs for the
player/barrel actor branch.  It compares the shrunken horizontal interval
x+3..x+12 for both actors and the full vertical interval y..y+15, then routes
contact through the raw-0xA7 actor state rather than through the normal static
collision helper.
"""
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.entities import PushableBarrel
from openagent.movement_collision import MovementCollisionMixin


class DummyMovement(MovementCollisionMixin):
    def __init__(self) -> None:
        self.player = SimpleNamespace(
            x=0.0,
            y=16.0,
            grounded=False,
            jump_anim_timer=0,
        )
        self.entities = SimpleNamespace(barrels=[], enemies=[])
        self.collision_enabled = True
        self._ignore_barrel_collision = None
        self._ignore_barrel_collision_ticks = 0
        self.solid_cells: set[tuple[int, int]] = set()
        self.score = 0
        self.sounds: list[int] = []
        self.popups: list[tuple[float, float, int]] = []

    def play_sound(self, sound_id: int) -> None:
        self.sounds.append(sound_id)

    def spawn_score_popup(self, x: float, y: float, value: int) -> None:
        self.popups.append((x, y, value))

    def cell_blocks_body(self, x: int, y: int) -> bool:
        return (x, y) in self.solid_cells

    def cell_solid(self, x: int, y: int) -> bool:
        return (x, y) in self.solid_cells

    def cell_blocks_floor(self, x: int, y: int, *, prev_bottom: float, new_bottom: float) -> bool:
        return False

    def actor_is_indestructible_solid(self, enemy) -> bool:
        return False

    def actor_contains_point(self, enemy, x: int, y: int) -> bool:
        return False


def check_visual_edge_touch_is_not_actor_overlap() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(32.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.player.x = 17.0  # full sprites touch/overlap, but x+3..x+12 does not.

    assert not dummy.player_overlaps_barrel(barrel)
    assert not dummy.player_collides()


def check_exact_side_push_moves_barrel_without_self_blocking() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(32.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.player.x = 22.0  # one pixel before the shrunken x intervals touch.

    blocked = dummy.move_axis_pixels(1, 0)

    assert not blocked
    assert dummy.player.x == 23.0, dummy.player.x
    assert barrel.x == 36.0, barrel.x
    assert not dummy.player_collides()


def check_blocked_side_push_enters_wall_pass_through_not_score_state() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(32.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.player.x = 22.0
    dummy.solid_cells.add((3, 1))  # blocks the 4px actor-step candidate at x=36.

    blocked = dummy.move_axis_pixels(1, 0)

    assert not blocked
    assert dummy.player.x == 23.0, dummy.player.x
    # Wall push must not be mapped to the destructive SAM1:0x848A score branch.
    assert barrel.x == 32.0, barrel.x
    assert barrel.direction == -1, barrel.direction
    assert barrel.code == 0xA7, hex(barrel.code)
    assert barrel.behavior_state == 0x1388, hex(barrel.behavior_state)
    assert barrel.transient_ticks == 0, barrel.transient_ticks
    assert barrel.wall_release_active
    assert barrel.body_pass_through
    assert dummy._ignore_barrel_collision is barrel
    assert dummy._ignore_barrel_collision_ticks == 1
    assert dummy.score == 0, dummy.score
    assert dummy.sounds == [], dummy.sounds
    assert dummy.popups == [], dummy.popups
    assert not dummy.player_collides()

    # Body is pass-through, but the top remains usable as a one-way platform.
    dummy.player.x = 32.0
    dummy.player.y = 0.0
    assert dummy.barrel_below() is barrel


def check_wall_pass_through_snaps_on_shrunken_edge_before_wall_probe() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(32.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.player.x = 22.0
    dummy.solid_cells.add((3, 1))

    dummy.move_axis_pixels(1, 0)
    assert barrel.wall_release_active

    # Pass 124 waited until p.x=35, when the player's collision probe was
    # already entering the wall tile.  The ASM-backed handoff uses the same
    # shrunken x+3..x+12 interval as SAM1:0x83C4: when the player's leading
    # shrunken edge reaches the barrel's leading shrunken edge, the full sprite
    # is still just short of the wall at x=48.
    dummy.move_axis_pixels(8, 0)
    assert dummy.player.x == 31.0, dummy.player.x
    assert barrel.x == 32.0, barrel.x
    assert barrel.wall_release_active
    assert barrel.body_pass_through

    dummy.move_axis_pixels(1, 0)

    assert dummy.player.x == 32.0, dummy.player.x
    assert barrel.x == 22.0, barrel.x
    assert barrel.direction == -1, barrel.direction
    assert not barrel.wall_release_active
    assert not barrel.body_pass_through
    assert not dummy.player_collides()


def check_wall_release_is_polled_from_atomic_horizontal_path() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(32.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.player.x = 22.0
    dummy.solid_cells.add((3, 1))

    dummy.move_axis_pixels(1, 0)
    assert dummy.player.x == 23.0, dummy.player.x
    assert barrel.x == 32.0, barrel.x
    assert barrel.wall_release_active
    assert barrel.body_pass_through

    # Regresses the pass-125 control-flow bug seen in the live runtime:
    # once the barrel body became pass-through, move_player_horizontal_tick()
    # stopped routing through move_axis_pixels(), so update_wall_release_barrels()
    # was never called and the barrel stayed stuck against the wall.
    blocked = dummy.move_player_horizontal_tick(9)

    assert not blocked
    assert dummy.player.x == 32.0, dummy.player.x
    assert barrel.x == 22.0, barrel.x
    assert barrel.behavior_state == 0x1388, hex(barrel.behavior_state)
    assert barrel.code == 0xA7, hex(barrel.code)
    assert not barrel.wall_release_active
    assert not barrel.body_pass_through
    assert not dummy.player_collides()

    # After restoration the barrel must be an ordinary pushable body again.
    blocked = dummy.move_player_horizontal_tick(-1)
    assert not blocked
    assert dummy.player.x == 31.0, dummy.player.x
    assert barrel.x == 18.0, barrel.x
    assert barrel.direction == -1, barrel.direction


def check_wall_release_restores_by_shrunken_clearance_not_full_tile() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(64.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.player.x = 64.0

    dummy.release_barrel_against_wall(barrel, 1)
    assert dummy.player_crossed_wall_release_barrel(barrel, 1)
    assert dummy.restore_wall_release_barrel_to_free_side(barrel, 1)

    assert barrel.x == 54.0, barrel.x
    assert barrel.x + 12 < dummy.player.x + 3




def check_wall_release_left_case_uses_mirrored_shrunken_clearance() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(64.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.player.x = 64.0

    dummy.release_barrel_against_wall(barrel, -1)
    assert dummy.player_crossed_wall_release_barrel(barrel, -1)
    assert dummy.restore_wall_release_barrel_to_free_side(barrel, -1)

    assert barrel.x == 74.0, barrel.x
    assert dummy.player.x + 12 < barrel.x + 3

def check_asm_1389_transient_moves_up_then_removes_actor() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(32.0, 64.0, code=0xAA, behavior_state=0x1389, transient_ticks=0x10)
    dummy.entities.barrels = [barrel]
    dummy._ignore_barrel_collision = barrel
    dummy._ignore_barrel_collision_ticks = 0x10

    for _ in range(15):
        dummy.update_barrels_tick()
        assert barrel in dummy.entities.barrels

    assert barrel.y == 34.0, barrel.y
    assert barrel.transient_ticks == 1, barrel.transient_ticks
    dummy.update_barrels_tick()

    assert barrel not in dummy.entities.barrels
    assert dummy._ignore_barrel_collision is None


def main() -> int:
    check_visual_edge_touch_is_not_actor_overlap()
    check_exact_side_push_moves_barrel_without_self_blocking()
    check_blocked_side_push_enters_wall_pass_through_not_score_state()
    check_wall_pass_through_snaps_on_shrunken_edge_before_wall_probe()
    check_wall_release_is_polled_from_atomic_horizontal_path()
    check_wall_release_restores_by_shrunken_clearance_not_full_tile()
    check_wall_release_left_case_uses_mirrored_shrunken_clearance()
    check_asm_1389_transient_moves_up_then_removes_actor()
    print("barrel player interaction checks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
