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

    def cell_blocks_body(self, x: int, y: int) -> bool:
        return False

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
    assert barrel.x == 33.0, barrel.x
    assert not dummy.player_collides()


def check_blocked_side_push_uses_transient_release_state() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(32.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.player.x = 22.0
    dummy.solid_cells.add((3, 1))  # blocks the candidate barrel position at x=33.

    blocked = dummy.move_axis_pixels(1, 0)

    assert not blocked
    assert dummy.player.x == 23.0, dummy.player.x
    # The decoded release branch owns a 0x10-tick transient; it does not write
    # a horizontal counter-step to actor_x, so the barrel must not visibly pop
    # one or more pixels away from the wall.
    assert barrel.x == 32.0, barrel.x
    assert dummy._ignore_barrel_collision is barrel
    assert dummy._ignore_barrel_collision_ticks == 0x10


def main() -> int:
    check_visual_edge_touch_is_not_actor_overlap()
    check_exact_side_push_moves_barrel_without_self_blocking()
    check_blocked_side_push_uses_transient_release_state()
    print("barrel player interaction checks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
