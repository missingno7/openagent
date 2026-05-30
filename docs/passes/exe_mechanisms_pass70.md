# EXE mechanisms pass 70 — overworld/UI 8x8 page split and menu/table text renderer

## Why this pass

The previous HUD passes fixed the `SAM?02.GFX` container and the status-bar page,
but the rest of the UI was still a blind spot.  The original game has more than
just the bottom status strip: the main menu, in-game tables and popup-style text
also use 8x8 assets.  These are not 16x16 level tiles.

## Camoto cross-check

The provided Camoto Studio source contains the game definition:

```xml
<file id="tls8-1" name="sam102.gfx" editor="tileset" format="tls-sagent-2k" filter="xor-sagent-8sprite" title="EGA sprites"/>
<file id="tls16-1" name="sam101.gfx" editor="tileset" format="tls-sagent-8k" filter="xor-sagent-16sprite" title="EGA tiles"/>
```

So the small UI graphics are correctly in `SAM?02.GFX` as 8x8 EGA sprites,
separate from the normal 16x16 `SAM?01.GFX` banks.

## ASM cross-check: three UI pages

The executable keeps three separate pointers into the decoded 8x8 sprite file:

| Pointer | Runtime meaning recovered so far | Runtime page |
|---|---|---:|
| `DS:6E36` | menu/table text range, ASCII `0x20..0x48` | `tiles8 bank 0` |
| `DS:6E3A` | menu/table text range, ASCII `0x5D..0x75` | `tiles8 bank 1` |
| `DS:6E32` | HUD/status digits and icons | `tiles8 bank 2` |

This explains why the HUD icons are near the end of the third 2k block while
menu and table text visibly live in the earlier blocks.

## ASM text renderer branch

The routine starting around `SAM1:0x18822` is the generic text/table renderer.
The currently decoded normal 8x8 branches are:

```text
SAM1:0x18908..0x18953  char 0x20..0x48 -> DS:6E36 + (ch - 0x20 + 0x0A) * 0x28 - 0x25
SAM1:0x188CF..0x18905  char 0x5D..0x75 -> DS:6E3A + (ch - 0x5D + 0x15) * 0x28 - 0x25
```

Because each `SAM?02.GFX` block has a three-byte header, these become tile IDs:

```text
0x20..0x48 -> bank 0, tile = ch - 0x20 + 9
0x5D..0x75 -> bank 1, tile = ch - 0x5D + 20
```

Later branches at `0x18960+` draw special symbols/large UI pieces from other
loaded graphics pointers (`DS:6DA6`, `DS:6D72`, `DS:6D76`, `DS:6D7E`, `DS:6D86`,
...).  Those are documented as not fully decoded yet; they likely cover table
borders, special menu symbols and popup decorations.

## Implementation

- Added `UI_TEXT_PAGE_0`, `UI_TEXT_PAGE_1` and `UI_HUD_PAGE` constants.
- Added `ui_text_tile_ref()` and `draw_ui_text_8x8()` to runtime.
- Kept HUD/status drawing on `UI_HUD_PAGE` / `DS:6E32`.
- Replaced the prototype overworld entrance number overlay's PIL text with real
  `SAM?02.GFX` 8x8 digit sprites.  This overlay is still a prototype helper, not
  claimed as an original-game popup.

## Remaining blind spots

- The real main-menu/table border renderer needs the later `0x18960+` special
  branches decoded.
- The overworld's exact level-selection popup/table flow has not yet been
  reimplemented.  The current runtime still directly enters a mission when the
  player is near an entrance and presses Enter/Space.
