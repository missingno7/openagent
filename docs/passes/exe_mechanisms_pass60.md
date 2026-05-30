# EXE mechanisms pass 60 — Camoto-verified SAM?02.GFX HUD decode

## Why pass 59 was wrong

Pass 59 removed the three-byte sub-tileset header from `SAM?02.GFX`.  That made
some cells appear like CGA/noise and also shifted the status-bar glyph indices.
The Camoto Studio game description (`data/games/secret-agent.xml`) identifies
`sam102.gfx`/`sam202.gfx`/`sam302.gfx` as:

- `format="tls-sagent-2k"`
- `filter="xor-sagent-8sprite"`
- title `EGA sprites`

The actual decoder is in the Camoto libraries, not the Studio GUI source.  The
relevant source chain is:

- `libgamegraphics/src/tls-sagent.cpp`: `TilesetType_SAgent2k` is Secret Agent's
  wrapper around the Crystal Caves tileset handler, with
  `SAM_PAD_TILES8 = 2048 - 3 - 2000`.
- `libgamegraphics/src/tls-ccaves-main.cpp`: each sub-tileset begins with a
  3-byte header: `numTiles`, `widthBytes`, `height`.
- `libgamegraphics/src/tls-ccaves-sub.cpp`: individual tiles start at offset 3,
  and dimensions are `widthBytes * 8` by `height`.
- `libgamearchive/src/filter-xor-sagent.cpp`: the 8x8 sprite filter resets the
  Secret Agent XOR/bitswap transform every 2048 bytes.

For Secret Agent 8x8 sprites, decrypted blocks begin with:

```text
32 01 08
```

That is 50 sprites, 1 byte wide (=8 px), 8 pixels high.  Each sprite is
`1 * 8 * 5 = 40` bytes, so the block is:

```text
3-byte header + 50 * 40-byte masked EGA sprites + 45 bytes padding = 2048 bytes
```

## Cross-reference with the HUD ASM

The status redraw routine uses `DS:6E32` as the in-memory pointer to this 8x8
sprite data.  Its address math confirms that `DS:6E32` points at the start of the
headered block, not at tile 0 data:

```asm
; digit source address
(ax = ascii_digit - 0x2F) * 0x28 + DS:6E32 - 0x25
```

For ASCII `'0'` this becomes `DS:6E32 + 3`, exactly the first tile data byte after
the three-byte header.  This matches Camoto's `CC_FIRST_TILE_OFFSET = 3`.

Known status-bar offsets now map as:

| ASM offset from `DS:6E32` | Sprite tile |
| --- | ---: |
| digit 0 | 0 |
| digit 1 | 1 |
| ... | ... |
| `0x0193` | 10 |
| `0x01BB` | 11 — life icon |
| `0x01E3` | 12 |
| `0x020B` | 13 |
| `0x02AB` | 17 |
| `0x02D3` | 18 |
| `0x02FB` | 19 |
| `0x0323` | 20 |
| `0x034B` | 21 |

Lives are drawn by a loop over `DS:6A40`; the X coordinate is computed as
`base + 0x100 + (life_index << 3)` in the scrolling/status path, so each life is
one 8px cell.

## Implementation changes

- Restored headered Camoto-style `SAM?02.GFX` decoding in both the editor and
  runtime decoder.
- HUD digits now use bank/set 0 tiles `0..9`, not `30..39`.
- HUD life icon now uses bank/set 0 tile `11`, not bank 2 tile `11`.
- Inventory/status icons use the verified `DS:6E32` offsets above.
- Removed the invented `A:` ammo label from the original-asset path; the ASM
  status routine draws ammo digits directly into slots `0x0E` and `0x0F`.

## Remaining work

The exact meaning of status flags `DS:69E9..69F4` still needs labeling against
inventory gameplay.  The pixel sources and slot offsets are now grounded, but the
semantic names for several icons are still provisional.
