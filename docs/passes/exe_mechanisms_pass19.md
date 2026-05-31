# Pass 19 – data-derived animated tile/background mechanics

This pass focuses on animated tiles such as water.  The important correction is
that this is not handled as a random visual effect in `openagent/runtime.py`.
The animation groups are derived from the level/background data layout that the
renderer already had from the SAMLEV/Frenkel mapping.

## What the game data shows

Each level has a background code (`LevelInfo.bg_code`).  `BACKGROUND_MAP` maps
that code to a `(bank, tile)` pair.  Every known background code points at the
first tile of a four-tile block:

```text
767 -> bank 8 tiles 16..19   # blue water-looking group
771 -> bank 8 tiles 20..23
209 -> bank 11 tiles 8..11
213 -> bank 11 tiles 12..15
...
```

The map tokens `0x35`, `0x36`, and `0x37` are a second clue: they do not name a
fixed sprite.  The renderer reads the active level background and draws
`background_tile + 1`, `+2`, or `+3`.  In other words the game data encodes a
four-phase background/tile block, not one isolated image.

The extracted report is in:

- `docs/derived_mechanics/pass19_tile_animation_mechanics.json`

## Implementation

Added:

- `openagent/game_assets/tile_animations.py`
- `tools/extract_sa_tile_animation_mechanics.py`

Changed:

- `openagent/game_assets/render.py`
  - accepts `bg_frame`
  - renders the level background as `first_tile + bg_frame`
  - renders `0x35/0x36/0x37` as phase-shifted variants inside the same four-tile block
- `openagent/runtime.py`
  - advances `anim_ticks` on the DOS-like tick clock
  - rebuilds the cached level image only when the 4-frame background phase changes
  - keeps collision state independent of visual animation

The phase timing is currently `1 frame / 4 DOS ticks`, so a full 4-frame loop is
roughly 0.88 s at 18.2065 Hz.  That matches the idea of an old DOS tile effect
rather than a modern 60 Hz shimmer.

## Bug fixed while touching this area

`load_level()` rendered the static level image before resetting state like
`has_glasses`, `collected_cells`, and `opened_doors`.  That could make hidden
platforms or removed pickups visually stale after level changes/resets.  The
state reset now happens first, then the level image is rebuilt.

## Still open

This pass covers the four-frame background/tile phase system.  Separate actor
mechanics still need more EXE work:

- exact projectile slot motion and collision
- non-bank14 enemy dispatch states (`0x75`, `0x76`, etc.)
- player death/lives/checkpoint logic
- pushable barrels and switches
