# EXE mechanisms pass 99 — level-0 world-map collision table split

## Why this pass exists

User testing showed that the pass-98 overworld collision model still did not
match the original map.  The concrete regression was raw `0x55`: it is solid on
the original world map but became passable in the port.  The deeper issue was
that the port reused the mission map-token collision table for level 0.

## ASM evidence

Pass 98 correctly traced the movement/collision helper:

- `SAM1:0xBAF5..0xBC0A` — top-down level-0 movement branch.
- `SAM1:0xB7D9..0xB8B0` — player-origin 10x16 body probe helper.

This pass rechecked the map-token parser feeding the same runtime collision
buffer.  The branch at `SAM1:0x10811` checks:

```text
cmp DS:681C, 1
je  level-0 / world-map parser path
```

When that branch is taken, the parser compares against the token table beginning
at `CS:0x2E20` and calls the runtime cell setter at `SAM1:0x1059E`.  That setter
writes:

- `+0x1C6`, `+0x1C8`, `+0x1CA` visual/runtime IDs,
- `+0x1CC` body collision byte,
- `+0x1CD` foot/one-way byte.

The mission parser around `CS:0x66F9..0x68A7` is still correct for side-view
levels, but it is not correct for level 0.

## Corrected world-map body-solid tokens

The recovered level-0 parser marks these raw world-map tokens body-solid:

```text
0x42 0x43 0x44 0x45 0x46 0x47
0x55
0x61
0x66 0x67
0x6C transiently, then overwritten clear in the same parser case
0x77 writes a solid cell at dy=-1 plus a clear cell at dy=0
```

Notable user-facing corrections:

- raw `0x55` is now solid on the world map;
- raw `0x61` remains solid;
- raw `0x30` is not body-solid in the recovered `CS:0x2E20` table even though it
  can look like part of a blocking coast/terrain shape.

## Runtime changes

- Added `openagent/exe_world_collision.py`, generated from the world-map parser
  entries in `docs/derived_collision_tables_all/SAM1_runtime_collision_calls.json`.
- `build_runtime_collision_grid(..., world_map=True)` now chooses the world-map
  table instead of the mission table.
- `OpenAgentApp.runtime_collision_grid()` passes `world_map=self.is_world_map`.
- `tools/check_overworld_collision.py` now asserts the level-0 specific facts:
  raw `0x55` and `0x61` block, while raw `0x30` is body-clear according to the
  recovered ASM table.

## Remaining gaps

The movement helper is still cell-byte based: it samples `+0x1CC`, not a per-pixel
mask.  Apparent narrow gaps between terrain graphics are therefore likely caused
by the 10 px-wide player body rectangle plus which adjacent world tokens actually
set `+0x1CC`, not by a general pixel mask system.  Exact entrance popups,
completion flags, and camera clamps are still separate overworld tasks.
