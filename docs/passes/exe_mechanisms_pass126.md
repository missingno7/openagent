# Pass 126 — raw 0xA7 wall-release polling and state restoration

## Goal

Fix the live-runtime regression reported after pass 125: after pushing a raw
`0xA7` barrel into a wall, the barrel entered the reconstructed body-pass-through
/ top-solid release state, but walking through it did not restore the barrel on
the free side.  The barrel therefore remained stuck at the wall.

The user's observation remains a testcase.  The source of truth is still the
raw-`0xA7/state 0x1388` actor branch and the already decoded shrunken
player/barrel contact rectangle at `SAM1:0x83C4..0x842F`.  I still have not found
the exact EXE store that performs the wall-release free-side relocation.

## ASM evidence used

`SAM1:0x82E3..0x8542` keeps raw `0xA7/state 0x1388` in its actor branch until the
branch either exits normally or enters one of the separate destructive paths.
The branch then evaluates the player/actor overlap rectangle at
`SAM1:0x83C4..0x842F` using `x+3..x+12` for both bodies.

The important negative evidence from pass 123 still stands:
`SAM1:0x848A..0x84E9` is not wall-release.  It plays sound `0x04`, adds
`+0x03E8`, rewrites the visible object to `0x00AA`, enters state `0x1389`, and
therefore represents the destructive score effect, not the push-through wall
case.

## Python bug found

Pass 125 only polled `update_wall_release_barrels()` from `move_axis_pixels()`.
That worked in the unit test, but not in the normal runtime path:

1. a blocked push calls `release_barrel_against_wall()`;
2. the barrel body becomes pass-through;
3. because pass-through barrels are intentionally skipped by
   `player_touching_barrel()`, the next normal horizontal tick no longer falls
   back into `move_axis_pixels()`;
4. `move_player_horizontal_tick()` then moves atomically and never calls
   `update_wall_release_barrels()`;
5. the release window never resolves, so the barrel stays stuck at the wall.

## Python behavior change

`move_player_horizontal_tick()` now checks for any active wall-release barrel
before using the normal atomic static-map probe.  While such a barrel exists, it
routes the horizontal move through `move_axis_pixels()`, which polls
`update_wall_release_barrels()` after every pixel.

This is a control-flow fix, not a new state rule: the reconstructed release state
is still raw `0xA7/state 0x1388`, body-pass-through, and top-solid.  When the
free-side restoration succeeds, the barrel is explicitly back to ordinary
pushable body behavior:

- `code == 0xA7`
- `behavior_state == 0x1388`
- `wall_release_active == False`
- `body_pass_through == False`

A follow-up push from the other side is now covered by the regression test.

## Tests

`tools/check_barrel_player_interaction.py` now includes
`check_wall_release_is_polled_from_atomic_horizontal_path()`, which reproduces
the bug with the actual high-level call sequence:

1. enter wall-release with `move_axis_pixels(1, 0)`;
2. continue through the pass-through barrel using `move_player_horizontal_tick()`;
3. assert that the free-side restoration happens;
4. assert that a one-pixel push from the opposite side moves the barrel as a
   normal solid pushable actor again.

## Remaining gap

The exact wall-release relocation store in the DOS executable is still open.
Pass 126 fixes a real Python control-flow bug and keeps the state transition
consistent with the known ASM branch, but it does not claim that the relocation
candidate/tick is fully proven beyond the `x+3..x+12` evidence from pass 125.
