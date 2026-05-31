# EXE mechanisms pass 59 — corrected SAM?02.GFX / Camoto-style 8x8 HUD sprite decode

## Problem

Pass 58 proved that the HUD/font art is in `SAM?02.GFX`, but decoded each 2048-byte block as if it had a 3-byte ProGraphx header.  That made the cells appear shifted/noisy and made the HUD icon/font mapping look less reliable than it is.

The original game data and Camoto/ModdingWiki model distinguish these files:

- `SAM?01.GFX`: 16x16 masked EGA tiles, 8064-byte blocks, 3-byte header + 50 * 160-byte tiles.
- `SAM?02.GFX`: 8x8 masked EGA sprites for status-bar icons, font and menu/table text.  Each 2000-byte sprite set is padded to 2048 bytes.
- `SAM?03.GFX`: level data.

So `SAM?02.GFX` is separate from the normal 16x16 tile banks, but it is still an ordinary external game asset file, not an EXE-only embedded/noise block.

## Corrected `SAM?02.GFX` format

Each 2048-byte chunk is:

```text
50 sprites * 40 bytes = 2000 bytes
48 bytes padding
```

Each 8x8 sprite is:

```text
8 rows * 5 bytes per row = 40 bytes
row plane order: mask, blue, green, red, intensity
```

There is **no 3-byte header** in the 2k 8x8 sprite blocks.  The 3-byte header belongs to the 16x16 `SAM?01.GFX` tilesets only.  Starting at offset 3 shifts every row by three bytes and explains the corrupted/noisy pass58 atlas.

## Implementation changes

- `openagent.game_assets.graphics.decode_prographx_8x8()` now starts each 2k block at offset `0` and decodes exactly 50 sprites.
- `openagent.game_assets.graphics.decode_prographx_8x8()` is the single shared decoder now.
- HUD score digits now use the corrected UI font row: `SAM?02.GFX` set/bank 0, tiles `30..39`.
- The player-life icon remains `SAM?02.GFX` set/bank 2, tile `11`; with the corrected decode it matches the supplied 8x8 life icon sample much more closely.
- The temporary HUD layout is still not fully proven slot-for-slot from the EXE, but all visible HUD pixels now come from the correctly decoded external 8x8 asset.

## Remaining work

- Trace the exact status-bar blit table in the EXE so ammo, score, keys, disk and glasses use the exact original positions and tile IDs.
- Use the same `SAM?02.GFX` decode path for menus, dialog/table text and score screens.
