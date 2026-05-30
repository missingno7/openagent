# Pass 61 — HUD 8x8 sprite page selection

User feedback showed the HUD icons still looked wrong even though the 8x8 EGA
sprite decoder itself matched Camoto's `tls-sagent-2k` / `xor-sagent-8sprite`
format.  The missing piece was which 2k page the game uses for the status bar.

## Camoto cross-check

`data/games/secret-agent.xml` in Camoto Studio describes `SAM?02.GFX` as the 8x8
EGA sprite file.  It is a 6144-byte file split into three 0x800-byte
sub-tilesets.  Each sub-tileset has the ProGraphx-style header and 50 masked
8x8 EGA sprites.

## ASM cross-check

The loader around `SAM1:0x1BB9D..0x1BC10` allocates/loads three 0x800-byte
blocks into three far pointers:

- `DS:6E36`
- `DS:6E3A`
- `DS:6E32`

The status/HUD routine around `SAM1:0x181F1..0x1872A` always uses `LES DI,
DS:6E32`, so the HUD is drawn from the third loaded 0x800 block, not the first
one.  In the Python decoder this is `tiles8 bank 2`.

The previous pass used the correct headered decoding but mapped HUD digits and
icons to bank 0.  That showed the wrong page: mostly font/punctuation-style
cells.  The actual HUD page is the last one, with the cyan digits and colored
inventory/life icons.

## Offset mapping

`DS:6E32` points at the beginning of the third 0x800 block including the 3-byte
header.  The digit routine computes:

```asm
(ax = ascii_digit - 0x2F) * 0x28 + DS:6E32 - 0x25
```

For ASCII `'0'`, this becomes `DS:6E32 + 0x03`, exactly sprite 0 data after the
3-byte header.  Therefore score/ammo digits are `tiles8 bank 2, sprites 0..9`.

Fixed icon offsets are also relative to the same third block:

| ASM offset from `DS:6E32` | Python tile |
| --- | --- |
| `0x01BB` | bank 2 tile 11 — life icon |
| `0x01E3` | bank 2 tile 12 |
| `0x020B` | bank 2 tile 13 |
| `0x02AB` | bank 2 tile 17 |
| `0x02D3` | bank 2 tile 18 |
| `0x02FB` | bank 2 tile 19 |
| `0x0323` | bank 2 tile 20 |
| `0x034B` | bank 2 tile 21 |

## Runtime changes

- `draw_hud_digit_string()` now defaults to bank 2.
- `draw_hud_icon()` maps all status icons to bank 2.
- The earlier bank-0 mapping is retained only in documentation as the error from
  pass 60.
