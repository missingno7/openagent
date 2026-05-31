# Pass 20 – correction: static background variants vs real animated tiles

Pass 19 misinterpreted `BACKGROUND_MAP` four-tile groups as animation frames.
That was wrong.  Codes `0x35`, `0x36` and `0x37` are static variants of the
active level background tile.  In practice they are used as fixed background
light/shadow/lamp detail, not as time-varying animation phases.

## Actual animated tile case found in the EXE

The EXE has repeated renderer branches that special-case runtime visual id
`0x01F3`:

- `SAM1:0xE6ED`
- `SAM1:0xF609`
- `SAM1:0xFBBC`
- `SAM1:0x101AC`

The branch is:

```text
cmp ax, 0x01F3
jne normal_path
cmp word [0x6840], 0x10
jne alternate_bitmap
; draw one bitmap pointer
alternate_bitmap:
; draw the paired bitmap pointer
```

The runtime collision/draw table maps raw mission code `0x60` to `cA=0x01F3`.
The SAMLEV/Camoto atlas mapping maps raw `0x60` to bank 4 tile 48.  The paired
bitmap corresponds to bank 4 tile 0.  So the implemented animation is:

```text
bank 4 tile 48 <-> bank 4 tile 0
```

This matches the observed bank 4 two-frame animation rather than rotating level
backgrounds.

## Implementation changes

- `openagent/game_assets/tile_animations.py`
  - removed background animation groups
  - added `ANIMATED_TILES={(4,48): ((4,48),(4,0))}`
  - kept `background_variant_tile_ref()` as a static helper for `0x35..0x37`
- `openagent/game_assets/render.py`
  - no longer accepts/uses `bg_frame`
  - background base tile is static
  - map codes `0x35..0x37` draw static `background+1/+2/+3`
  - normal tile refs pass through `animated_tile_ref()`
- `openagent/runtime.py`
  - still re-renders cached level image on DOS ticks, but now only to animate
    actual animated tile refs, not the whole background block
- `tools/extract_sa_tile_animation_mechanics.py`
  - rewritten to report the corrected static-vs-animated distinction

## Open questions

The branch selection uses `DS:6840`, which is also involved in draw offset/state.
The current runtime uses a conservative DOS tick phase for the two-frame tile.
The next precision step is to fully map how the original renderer changes
`0x6840` across draw passes and whether this animation toggles every game tick,
every redraw pass, or only under specific level draw modes.
