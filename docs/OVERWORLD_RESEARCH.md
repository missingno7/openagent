# Overworld / island map research status

Level `00` is the top-down island map.  It must not be treated as a side-view
mission level even though it lives in the same `SAM?03.GFX` archive and uses the
same 42-byte rows / star-row layout.

## Current confirmed data facts

- Level index `0` is the island/world map in all three episodes.
- Raw `0x59` appears once in each episode's level 0 and is the world-map player
  marker/spawn candidate.
- Raw `0x4D/0x4E/0x4F/0x50` form exactly 16 entrance anchors per episode when
  counted in row-major map order.  `0x4D/0x4E` is one two-cell-wide building;
  `0x4F` and `0x50` are single-cell markers.  The prototype currently uses
  row-major order as the mission entrance list.
- The same raw byte can mean something different in world vs mission contexts.
  Example: mission raw `0x4D` is the landmine, but world raw `0x4D` is one of
  the entrance marker classes.

## Data inventory from level 0

| Episode | player marker | entrance marker counts | total entrances |
| --- | --- | --- | --- |
| 1 | `0x59` at `(4,2)` | `0x4D/0x4E`: 1 wide pair, `0x4F`: 9, `0x50`: 6 | 16 |
| 2 | `0x59` at `(4,4)` | `0x4D/0x4E`: 1 wide pair, `0x4F`: 14, `0x50`: 1 | 16 |
| 3 | `0x59` at `(36,6)` | `0x4D/0x4E`: 1 wide pair, `0x4F`: 0, `0x50`: 15 | 16 |

High-frequency world raw bytes include water/coast/tree-looking groups such as
`0x55`, `0x56..0x58`, `0x61..0x68`, and `0x42..0x47`.  Pass 99 proved that
level 0 must use the dedicated `CS:0x2E20` world parser table rather than the
mission parser table.  World raw `0x55` and `0x61` are body-solid; raw `0x30`
is body-clear in the recovered table.  Movement still samples the runtime body
byte `+0x1CC` at the player rectangle corners.

## Current runtime model

The prototype now keeps world-map logic in `openagent/overworld.py` so it is no
longer hidden inside `runtime.py`:

- `find_world_spawn()` uses raw `0x59` exactly as the player origin.
- `world_entrances()` scans `0x4D/0x4E/0x4F/0x50` in row-major order while
  collapsing adjacent `0x4D/0x4E` into one wide entrance anchor.
- `world_cell_blocked()` now reads the runtime collision cell body byte
  `+0x1CC`, matching the ASM helper traced in pass 98.
- Level 0 collision cells are built with `openagent/exe_world_collision.py`, the
  dedicated world-map parser table recovered in pass 99.
- `world_player_clear_at()` uses the ASM 10x16 player-origin rectangle
  (`x+3/x+12`, `y/y+15`).
- Walking into an entrance footprint enters the mission immediately;
  `try_enter_world_level()` remains only as a keyboard/backwards-compatible shortcut.
- Completed entrances are redrawn with bank-1 checked cels 16..19 after mission exit.
- `draw_world_entrance_numbers()` is explicitly a prototype overlay, not the
  original game popup/table renderer.

## What still needs ASM reverse engineering

The important unknowns are not in the data format anymore; they are in the EXE
logic:

1. **World movement and collision**
   - Pass 98 found the top-down update branch at `SAM1:0xBAF5..0xBC0A`.
   - Pass 98 found the collision helper at `SAM1:0xB7D9..0xB8B0`: it probes
     runtime `+0x1CC` at a 10x16 player-origin rectangle and ignores `+0x1CD`.
   - Remaining work: compare camera/viewport clamping and movement edge cases
     against DOSBox.

2. **Entrance mapping and completion flags**
   - Determine whether `0x4D`, `0x4F`, and `0x50` differ by state/availability.
   - Trace the exact mapping from entrance marker to level index.
   - Trace how completed levels are stored and how the map changes after exits.

3. **World popup/table renderer**
   - Reconstruct the table/window code that uses `SAM?02.GFX` pages 0 and 1.
   - Distinguish debug/prototype entrance labels from original title/level-name
     popups.

4. **Shared code with missions**
   - Determine which routines are shared with side-view missions: tile decoding,
     map row layout, 8x8 UI text, sound calls, and state transitions.
   - Keep mission collision and world collision separate until the shared
     boundary is proven.

## Accuracy policy

Everything in `openagent/overworld.py` should be read as either `data_verified`
(raw bytes and counts), `asm_partial` (movement/collision/camera/draw/entry after pass 102), or
`heuristic` (exact entrance-to-level mapping, persistent completion flags, popups).

## Pass 78 reproducible data audit

Added `tools/audit_overworld_data.py`, which regenerates the level-0 inventory
from the original data files.  The generated snapshot lives at:

```text
_docs note_: docs/registry/overworld_level0_inventory.json
```

Use it like this:

```bash
python tools/audit_overworld_data.py
python tools/audit_overworld_data.py --json > docs/registry/overworld_level0_inventory.json
```

This is intentionally **data-only**.  It confirms marker positions and counts,
pass 98 proves the core movement collision helper, and pass 99 proves the
separate world-map collision table.  Entrance mapping,
completion flags, camera clamp, and popup behavior remain ASM tasks.


## Pass 98 movement/collision audit

The broad `WORLD_BLOCKED_CODES` visual heuristic has been removed from runtime
movement.  `SAM1:0xB7D9..0xB8B0` tests the runtime collision buffer exactly like
mission body checks: four corners of a 10x16 origin rectangle sample byte
`+0x1CC`.  The top-down movement branch at `SAM1:0xBAF5..0xBC0A` checks the
destination first and skips blocked moves instead of moving into a wall and
resolving backward.

This means many visually water/coast/tree-looking raw codes are not automatically
blocking.  Only cells whose runtime writes leave body byte `+0x1CC` non-zero
block the overworld player.


## Pass 99 world collision table split

The previous pass still reused the mission collision parser for level 0.  That
was wrong: `SAM1:0x10811` branches on `DS:681C == 1` into the level-0 parser
whose token table starts at `CS:0x2E20`.  Runtime now passes
`world_map=True` when building the collision grid for level 0.

Important consequences:

- `0x55` is body-solid on the world map.
- `0x61` is body-solid on the world map.
- `0x30` remains body-clear according to the recovered table, even if its
  graphics look like part of a solid terrain edge.
- The apparent ability to fit between some terrain graphics is still consistent
  with the ASM helper because the player collision body is only 10 px wide
  (`x+3..x+12`) and the helper samples cell bytes, not the full 16 px sprite.


## Pass 100 world movement and camera reconstruction

User testing showed that the pass-99 collision table was closer but the actual
feel/navigation still diverged.  The issue was that runtime still mixed the
world-map collision helper with generic movement/camera assumptions.

Pass 100 re-read `SAM1:0xBAF5..0xBC0A` and now models these level-0 specifics:

- attempted movement is checked as a displacement before writing player X/Y;
- no pre-clamp to the 16x20 decoded sprite bounds is applied before collision;
- direction flags are processed in the EXE order: right, left, down, up;
- vertical movement is fixed at 4 px/tick;
- horizontal movement still uses the shared `0x532D` step ramp;
- camera rendering uses reconstructed `DS:6838/683A` registers with margins
  `0xAA`, `0x96`, `0x50` and clamps `0x140`, `0xB8`;
- entering/resetting the overworld and world-map teleport arrival initialize the
  camera as `player_x-0xA0`, `player_y-0x64`, then clamp.

The pass-99 world collision table is intentionally unchanged.  Raw `0x55` and
`0x61` remain body-solid, while raw `0x30` remains body-clear per `CS:0x2E20`.


## Pass 101 world draw/entry/completion pass

The collision helper is still the ASM 10x16 origin rectangle (`x+3/x+12`,
`y/y+15`).  The apparent oversized collision came from the prototype drawing
the world player at `(-2,-1)` and spawning at `0x59 + (2,1)`, which separated
the visible sprite from `DS:34EE/34F0`.  Pass 101 removes those visual/origin
fudges and draws the player from the normal `DS:3500/34F6` animation family.

Walking into `0x4D/0x4E/0x4F/0x50` building footprints now enters the
corresponding row-major mission immediately.  Completing a mission returns to
level 0, release-gates the current building to avoid instant re-entry, and
redraws that entrance using the checked bank-1 cels 16..19.

Still open: the original entrance dispatch table/flags and popup/table UI.

## Pass 102 regression fixes

Raw `0x59` is now treated purely as the level-0 player marker and is skipped
from static world rendering.  The live player draw path is the only thing that
paints the player after load, so the start marker no longer remains as a second
sprite.

Completed/checkmarked houses remain active entrances.  The release gate after
returning from a mission now uses the player origin inside the building
footprint; once the origin leaves and later re-enters, the level can be opened
again.

Still open: exact entrance-to-level mapping, original popup/table UI, and
persistent save/progression flags.
