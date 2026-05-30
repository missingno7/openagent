# Pass 77 — Overworld isolation and accuracy status

This pass is intentionally not a gameplay-claim pass.  It prepares the project
for a real ASM audit of level `00`, the top-down island/overworld map.

## Code cleanup

Moved prototype overworld logic out of `runtime.py` into:

```text
openagent/overworld.py
```

The new `OverworldMixin` owns:

- `find_world_spawn()`
- `world_entrances()`
- `world_cell_blocked()`
- `world_player_blocked()`
- `move_world_axis()`
- `try_enter_world_level()`
- `draw_world_entrance_numbers()`

This makes it obvious which pieces are still heuristic and prevents mission
platformer collision logic from being confused with world-map collision logic.

## Data facts recorded

Level 0 inventory confirms:

| Episode | player marker | entrance marker counts | total entrances |
| --- | --- | --- | --- |
| 1 | `0x59` at `(4,2)` | `0x4D`: 1, `0x4F`: 9, `0x50`: 6 | 16 |
| 2 | `0x59` at `(4,4)` | `0x4D`: 1, `0x4F`: 14, `0x50`: 1 | 16 |
| 3 | `0x59` at `(36,6)` | `0x4D`: 1, `0x4F`: 0, `0x50`: 15 | 16 |

Important correction for future work: raw `0x4D` is context-sensitive.  In
missions it is the landmine; in level 0 it is one of the entrance marker codes.

## Status

- Data/layout facts: `data_verified`.
- Collision behavior: `heuristic`.
- Entrance-to-level mapping: `heuristic`.
- Popups/table windows: `unimplemented` except for the shared 8x8 renderer.

## Next ASM pass

The next useful reverse-engineering step is to search the unpacked EXE for the
level-0 mode branch rather than trying to tune world collision visually.  The
trace should identify:

1. top-down player movement routine,
2. tile/block test routine used by the island map,
3. interaction branch for entrance markers,
4. completion flag writes after returning from a mission,
5. table/popup renderer calls for level names or menus.
