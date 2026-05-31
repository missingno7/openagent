#!/usr/bin/env python3
"""Regression checks for raw 0xA7 vertical fall semantics.

The falling barrel must keep its X coordinate and use foot/landing probes for
vertical support.  A side body tile that overlaps the barrel's broad 16x16 AABB
must not stop gravity; horizontal push collision still uses that broad test.
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
        self.entities = SimpleNamespace(barrels=[])
        self.side_solids: set[tuple[int, int]] = set()
        self.floor_solids: set[tuple[int, int]] = set()

    def cell_solid(self, x: int, y: int) -> bool:  # used by barrel_collides/try_push only
        return (x, y) in self.side_solids or (x, y) in self.floor_solids

    def cell_blocks_floor(self, x: int, y: int, *, prev_bottom: float, new_bottom: float) -> bool:
        return (x, y) in self.floor_solids


def check_side_body_does_not_stop_vertical_fall() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(17.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.side_solids.add((2, 1))

    assert dummy.barrel_collides(barrel), "test setup should overlap side solid under broad AABB"
    moved = dummy.move_barrel_vertical(barrel, 3)

    assert moved == 3, moved
    assert barrel.x == 17.0, barrel.x
    assert barrel.y == 19.0, barrel.y
    assert not barrel.grounded


def check_floor_probe_still_lands_barrel() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(17.0, 16.0)
    dummy.entities.barrels = [barrel]
    dummy.floor_solids.add((1, 2))

    moved = dummy.move_barrel_vertical(barrel, 3)

    assert moved == 0, moved
    assert barrel.x == 17.0, barrel.x
    assert barrel.y == 16.0, barrel.y
    assert barrel.grounded
    assert barrel.fall_ticks == 0


def check_push_over_edge_marks_barrel_unsupported_before_fall_tick() -> None:
    dummy = DummyMovement()
    barrel = PushableBarrel(29.0, 16.0)
    barrel.grounded = True
    dummy.entities.barrels = [barrel]
    dummy.floor_solids.add((1, 2))  # supports x=29 but not x=30 with x+3/x+12 probes.

    moved = dummy.try_push_barrel(barrel, 1)

    assert moved
    assert barrel.x == 30.0, barrel.x
    assert not barrel.grounded


def main() -> int:
    check_side_body_does_not_stop_vertical_fall()
    check_floor_probe_still_lands_barrel()
    check_push_over_edge_marks_barrel_unsupported_before_fall_tick()
    print("barrel vertical fall checks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
