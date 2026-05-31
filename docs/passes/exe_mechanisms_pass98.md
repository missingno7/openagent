# EXE mechanisms pass 98 — level-0 overworld movement and collision

Scope: replace the prototype level-0 collision heuristic with the ASM movement
predicate used by the original top-down island map.

## ASM trace

Relevant SAM1 sites:

- `SAM1:0x035B..0x044B` — keyboard ISR branch sets the extra overworld
  up/down flags only when `DS:681C == 1`, i.e. the EXE's one-based level-0
  island map.
- `SAM1:0xBAF5..0xBC0A` — top-down player movement routine:
  - left/right call helper `0x532D` to update `DS:681E/DS:6820`, then test the
    proposed horizontal step before changing `DS:34EE`;
  - down tests `(dx=0, dy=+4)`, then adds `+4` to `DS:34F0`;
  - up tests `(dx=0, dy=-4)`, then subtracts `4` from `DS:34F0`.
- `SAM1:0xB7D9..0xB8B0` — top-down collision helper:
  - builds a 10x16 player-origin rectangle from `DS:34EE+3`, `DS:34EE+12`,
    `DS:34F0+0`, and `DS:34F0+15`;
  - samples the runtime cell body byte `+0x1CC` at the four rectangle corners;
  - ignores the foot/one-way byte `+0x1CD` for overworld navigation;
  - returns clear only when all four body samples are zero.

## Important correction

The previous `WORLD_BLOCKED_CODES` model was a visual guess.  It blocked broad
water/coast/tree raw byte ranges such as `0x55`, `0x56..0x68`, and
`0x42..0x47`.  The ASM does not do that.  It uses the same runtime collision
cell buffer and reads only `+0x1CC`.

With the currently recovered runtime-cell writes, level-0 body-solid source
codes are narrow and stable across the three episodes: notably `0x43`, `0x46`,
`0x61`, and the upper cell written by teleporter raw `0x77`.  Water/coast codes
that write only visuals or foot bytes are not body blockers for the top-down
movement helper.

## Runtime changes

- `openagent/overworld.py` no longer imports or uses `WORLD_BLOCKED_CODES`.
- `world_cell_blocked()` now reads `runtime_collision_cell(...).body_solid`,
  matching the `+0x1CC` test.
- `world_player_clear_at()` mirrors the ASM 10x16 origin rectangle.
- `move_world_axis()` now tests the destination before moving.  Blocked movement
  is skipped; the old pixel rollback loop was removed.
- World movement now runs on DOS fixed ticks:
  - horizontal: `horizontal_step_for_hold_ticks()` / helper `0x532D` ramp,
  - vertical: fixed `4 px/tick` up/down steps.
- World teleport countdown now advances on DOS ticks instead of the Tk render
  cadence because world movement is fixed-tick driven.

## Still open

- Entrance-to-level mapping for raw `0x4D/0x4F/0x50` is still row-major
  prototype behavior.
- Completion flags and original popup/table windows are still not traced.
- Camera bounds are now closer because movement uses fixed ticks, but the exact
  original map viewport clamp should still be compared against DOSBox/ASM.
