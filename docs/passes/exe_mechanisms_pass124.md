# Pass 124 - raw 0xA7 wall-release free-side handoff

## Goal

Tighten the remaining wall-release behavior for the raw `0xA7` pushable barrel:
when a barrel is pushed into a wall, the player can pass through the barrel body,
walk almost to the wall, and then the barrel shifts to the free side so it can be
pushed back from the other side.

The user's description is treated as a testcase.  The ASM facts still matter
more than the description, so this pass keeps the destructive `0x1389` branch
separate and only narrows the reconstructed wall-release handoff.

## ASM facts / negative proof

The relevant raw-barrel actor range remains `SAM1:0x82E3..0x8742`.

Facts carried forward:

- `SAM1:0x83C4..0x848A` uses the shrunken player/barrel rectangle:
  player/actor `x+3..x+12`, and full `y..y+15`.
- `SAM1:0x848A..0x84E9` is still the destructive/score rewrite:
  sound `0x04`, score `+0x03E8`, visible object `0x00AA`, state `0x1389`,
  timer `0x10`.
- `SAM1:0x8542..0x8742` state `0x1389` moves Y upward by `2 px/tick` and
  removes/cleans up the actor after the timer expires.

The exact ASM store for the wall-release X restoration is still not isolated.
However, this pass improves the reconstruction by matching the observed trigger
condition more closely: the barrel must not snap merely because the player has
started crossing the pass-through body.  It should snap only once the player has
crossed through the shrunken barrel rectangle and the player's leading body
probe is immediately against the blocking wall.

## Runtime changes

`update_wall_release_barrels()` now uses three explicit substeps:

1. `player_crossed_wall_release_barrel()` checks that the player has crossed the
   shrunken raw-0xA7 overlap rectangle.
2. `player_front_wall_for_barrel_release()` probes one pixel beyond the player's
   leading collision edge (`x+12+1` to the right, `x+3-1` to the left) on the
   normal body rows.  Without this wall gate the barrel remains pass-through and
   does not snap early.
3. `restore_wall_release_barrel_to_free_side()` places the barrel on the free
   side of the player and re-enables normal body collision if the broad
   barrel/world collision check accepts that position.

For a rightward push into a right wall, the player ends between wall and barrel;
the barrel is restored immediately to the player's left.  The leftward case is
mirrored.

## Tests

`tools/check_barrel_player_interaction.py` now covers the wall-release handoff
with a static wall cell:

- blocked push enters raw `0xA7/state 0x1388` pass-through, not score/destruction;
- the barrel stays in place while the player passes through but is not yet at
  the wall;
- on the next pixel, when the leading player probe is one pixel before the wall,
  the barrel snaps to the free side and returns to normal body collision;
- without a front wall, the temporary pass-through state does not snap early.

## Still open

- exact ASM path/store for the wall-release X restoration;
- DOSBox pixel capture for the final snap amount and timing;
- pushed-off-edge fall timing after a horizontal push;
- helper `0x547C` projectile-hit branch for raw `0xA7`.
