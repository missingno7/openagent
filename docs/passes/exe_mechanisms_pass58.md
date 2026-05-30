# EXE mechanisms pass 58 — SAM?02.GFX HUD/font asset decode and death-tile crash fix

## 1. Crash fix

Pass 57 referenced `PLAYER_DEATH_TILES` from `openagent.animation` but did not
import it in `openagent.runtime`.  This caused:

```text
NameError: name 'PLAYER_DEATH_TILES' is not defined
```

when the player entered the death draw path, for example after stepping on an
armed landmine.  Runtime now imports the constant and the death countdown can
render without crashing.

## 2. HUD art was not in SAM?01.GFX

The user-provided life icon and the in-game HUD confirm that the small HUD/menu
art is not stored in the normal 16x16 tile banks.  The missing asset is
`SAM?02.GFX`:

- `SAM?01.GFX`: 16x16 masked EGA tiles, 16 banks x 50 tiles.
- `SAM?02.GFX`: 8x8 masked EGA cells for HUD digits/icons and menu/table text.
- `SAM?03.GFX`: level archives.

The earlier DS:6E32 note was only observing the in-memory pointer used by the
status redraw code.  It was misleading as an asset-location claim: that backing
art is loaded from/decrypted out of `SAM?02.GFX`, not invented by the EXE and
not part of the 16x16 banks.

## 3. SAM?02.GFX format

`SAM?02.GFX` is encrypted with the same Secret Agent bit-reversal/XOR transform,
but with key reset every `2048` bytes.  It contains three 2048-byte banks.
Each bank has a 3-byte header followed by 8x8 masked EGA cells:

```text
cell size = 8 rows * 1 byte-wide cell * 5 planes = 40 bytes
planes    = opaque mask, blue, green, red, intensity
```

The decoded episode 1 `SAM102.GFX` banks have 51 usable cells each.  The visible
structure matches the game:

- bank 0: mixed punctuation/numbers/symbols;
- bank 1: uppercase menu/table letters;
- bank 2: HUD/status digits `0..9`, colon and small status icons.

The provided life icon matches `SAM102.GFX` bank 2 tile 11.

## 4. Runtime implementation

Added a real 8x8 decoder:

```text
secret_agent_editor.graphics.Tileset8
secret_agent_editor.graphics.decode_prographx_8x8()
```

`secret_agent_editor.bundle.Episode` now carries `tiles8` alongside `tiles16`.
`openagent.runtime.draw_status_bar()` now uses the decoded `SAM?02.GFX` cells
for the bottom 8px HUD strip instead of hand-made PIL masks:

- score digits: bank 2 tiles 0..9;
- colon: bank 2 tile 10;
- life icon: bank 2 tile 11;
- adjacent inventory icons are now drawn from the same real 8x8 bank instead of
  temporary point masks.

The exact x-slot layout still needs a more complete pass through the status bar
ASM, but the pixels are now sourced from the original game asset.

## 5. Remaining work

- Annotate the full status redraw slot table so ammo, keys, disk/glasses and
  other inventory icons land at exactly the original x positions.
- Trace which `SAM?02.GFX` bank/tile each status flag uses instead of using the
  current adjacent-icon mapping for non-life inventory icons.
- Use the same `Tileset8` decoder for menus, score tables and any other text
  screens that draw from the small-font asset.
