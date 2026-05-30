# Overworld / island map research status

Level `00` is the top-down island map.  It must not be treated as a side-view
mission level even though it lives in the same `SAM?03.GFX` archive and uses the
same 42-byte rows / star-row layout.

## Current confirmed data facts

- Level index `0` is the island/world map in all three episodes.
- Raw `0x59` appears once in each episode's level 0 and is the world-map player
  marker/spawn candidate.
- Raw `0x4D`, `0x4F`, and `0x50` appear exactly 16 times total per episode when
  counted in row-major map order.  The prototype currently uses that as the
  mission entrance list.
- The same raw byte can mean something different in world vs mission contexts.
  Example: mission raw `0x4D` is the landmine, but world raw `0x4D` is one of
  the entrance marker classes.

## Data inventory from level 0

| Episode | player marker | entrance marker counts | total entrances |
| --- | --- | --- | --- |
| 1 | `0x59` at `(4,2)` | `0x4D`: 1, `0x4F`: 9, `0x50`: 6 | 16 |
| 2 | `0x59` at `(4,4)` | `0x4D`: 1, `0x4F`: 14, `0x50`: 1 | 16 |
| 3 | `0x59` at `(36,6)` | `0x4D`: 1, `0x4F`: 0, `0x50`: 15 | 16 |

High-frequency world raw bytes include water/coast/tree-looking groups such as
`0x55`, `0x56..0x58`, `0x61..0x68`, and `0x42..0x47`.  The current collision
classification for these is still heuristic.

## Current runtime model

The prototype now keeps world-map logic in `openagent/overworld.py` so it is no
longer hidden inside `runtime.py`:

- `find_world_spawn()` uses raw `0x59`.
- `world_entrances()` scans `0x4D/0x4F/0x50` in row-major order.
- `world_cell_blocked()` uses an explicit heuristic set of water/coast/tree
  codes.
- `try_enter_world_level()` enters the nearest candidate when the player presses
  enter/space.
- `draw_world_entrance_numbers()` is explicitly a prototype overlay, not the
  original game popup/table renderer.

## What still needs ASM reverse engineering

The important unknowns are not in the data format anymore; they are in the EXE
logic:

1. **World movement and collision**
   - Find the top-down movement update branch.
   - Identify whether the player probes are tile-centered, 8x8-based, or use
     a smaller hitbox than the side-view player.
   - Replace `WORLD_BLOCKED_CODES` with a table/branch recovered from ASM.

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
(raw bytes and counts) or `heuristic` (collision, exact entry behavior, popups)
until a dedicated ASM trace upgrades it.

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
but does not prove collision, entrance mapping, or popup behavior.  Those remain
ASM tasks.
