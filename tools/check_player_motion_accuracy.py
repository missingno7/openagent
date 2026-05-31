#!/usr/bin/env python3
"""Regression checks for normal mission player motion edge cases.

Pass 130 covers a one-tile doorway case reported while jumping/falling against a
wall. Pass 131 fixes the vertical table indexing used by that case: the EXE
initializes bytes 0x34B0..0x34C2 and indexes them as byte[0x34AF + counter], so
DS:34EA=1 consumes a zero step.  That zero first jump tick plus the later
1,1,2,2,2 fall sequence creates the modulo-16 doorway alignment frame.
"""
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.player import Player
from openagent.runtime import OpenAgentApp
from openagent.game_assets.constants import TILE


class PlayerMotionProbe(OpenAgentApp):
    def __init__(self) -> None:
        # Do not call OpenAgentApp.__init__ because it creates the Tk window.
        self.player = Player()
        self.keys: set[str] = set()
        self.collision_enabled = True
        self.level_index = 2  # mission branch where B7D9 may reset DS:681E on block
        self.entities = SimpleNamespace(barrels=[], enemies=[], platforms=[])
        self._ignore_barrel_collision = None
        self._ignore_barrel_collision_ticks = 0
        self.solid_cells: set[tuple[int, int]] = set()
        self.sounds: list[int] = []

    def update_teleport_tick(self) -> bool:
        return False

    def try_fire_projectile(self) -> bool:
        return False

    def play_sound(self, sound_id: int) -> None:
        self.sounds.append(sound_id)

    def cell_blocks_body(self, x: int, y: int) -> bool:
        return (x, y) in self.solid_cells

    def cell_blocks_floor(self, x: int, y: int, *, prev_bottom: float, new_bottom: float) -> bool:
        return (x, y) in self.solid_cells

    def cell_blocks_foot(self, x: int, y: int) -> bool:
        return (x, y) in self.solid_cells

    def runtime_collision_cell(self, x: int, y: int):
        return SimpleNamespace(body_solid=True, foot_solid=True, source_code=0) if (x, y) in self.solid_cells else None


def check_jump_alignment_is_visible_to_horizontal_probe() -> None:
    probe = PlayerMotionProbe()
    # Vertical wall column x=4 with a single 16px clear opening at row y=3.
    # Candidate player x=66 gives B7D9 samples x+3=69 and x+12=78, both inside
    # tile column 4.  At y=49 the bottom sample is row 4 and collides with the
    # lower wall block; after the first jump ascent y=48, both Y samples are in
    # the opening row 3 and horizontal movement must be allowed.
    probe.solid_cells.update({(4, 2), (4, 4)})
    probe.player.x = 70.0
    probe.player.y = 49.0
    probe.player.grounded = True
    probe.player.fall_ticks = 0
    probe.keys = {"Left", "space"}

    # Demonstrate the regression: the raw horizontal helper would reject before
    # BC0E has had a chance to align Y by one pixel.
    assert probe.move_player_horizontal_tick(-4), "horizontal-first B7D9 should see the lower corner block at y=49"
    assert probe.player.x == 70.0, probe.player.x

    # Reset and run the real player tick.  Pass 130 makes the BC0E jump phase
    # happen before the horizontal destination probe, so the same tick moves up
    # to y=48 and then enters the one-tile opening.
    probe.player.x = 70.0
    probe.player.y = 49.0
    probe.player.grounded = True
    probe.player.fall_ticks = 0
    probe.player.jump_anim_timer = 0
    probe.player.move_hold_ticks = 3  # next tick uses a 4px step
    probe.keys = {"Left", "space"}

    probe.update_player_tick()

    assert probe.player.y == 48.0, probe.player.y
    assert probe.player.x == 66.0, probe.player.x
    assert not probe.player_collides(), "10x16 body should fit exactly inside the one-tile opening"


def check_player_vertical_table_is_unshifted_from_asm() -> None:
    from openagent.game_constants import PLAYER_VERTICAL_STEP_TABLE
    from openagent.player_motion import advance_fall_tick, advance_jump_tick

    # SAM1:0x28ED6 writes 0x34B0 = 0 and B8B3/BD22 read
    # byte[0x34AF + DS:34EA] after incrementing DS:34EA.  Counter 1 must
    # therefore consume a zero step; counter 2 is the first 8px movement.
    assert PLAYER_VERTICAL_STEP_TABLE[1] == 0
    assert PLAYER_VERTICAL_STEP_TABLE[2] == 8

    counter = 0
    jump_steps: list[int] = []
    jump_active = True
    while jump_active:
        counter, jump_active, step = advance_jump_tick(counter)
        jump_steps.append(step)
    assert jump_steps == [0, 8, 8, 8, 4, 4, 2, 2, 2, 2], jump_steps
    assert sum(jump_steps) == 40
    assert counter == 9

    fall_steps: list[int] = []
    for _ in range(5):
        counter, step = advance_fall_tick(counter)
        fall_steps.append(step)
    assert fall_steps == [1, 1, 2, 2, 2], fall_steps
    # From a tile-aligned jump start, the 40px ascent leaves y at +8 mod 16.
    # The first five fall ticks then add 8px total and create a real tile-
    # aligned doorway-entry frame.  The old shifted table produced 9px here.
    assert sum(fall_steps) == 8


def check_falling_jump_arc_gets_tile_aligned_doorway_frame() -> None:
    probe = PlayerMotionProbe()
    for row in range(0, 9):
        if row != 3:
            probe.solid_cells.add((4, row))
    for col in range(5, 9):
        probe.solid_cells.add((col, 6))

    probe.player.x = 84.0
    probe.player.y = 80.0
    probe.player.grounded = True
    probe.player.fall_ticks = 18
    probe.player.jump_anim_timer = 0
    probe.player.move_hold_ticks = 0

    entered_opening = False
    aligned_frames: list[tuple[int, float, float]] = []
    for tick in range(24):
        probe.keys = {"Left", "space"}
        probe.update_player_tick()
        if int(probe.player.y) % 16 == 0:
            aligned_frames.append((tick, probe.player.x, probe.player.y))
        # Player's B7D9 X footprint is now inside the wall column while top and
        # bottom are both in the one clear row.
        if 61 <= probe.player.x <= 67 and probe.player.y == 48.0:
            entered_opening = True
            break

    assert aligned_frames, "jump/fall table should create modulo-16 frames"
    assert entered_opening, (probe.player.x, probe.player.y, aligned_frames)


def main() -> int:
    check_player_vertical_table_is_unshifted_from_asm()
    check_jump_alignment_is_visible_to_horizontal_probe()
    check_falling_jump_arc_gets_tile_aligned_doorway_frame()
    print("player motion accuracy checks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
