# Pass 93 — HUD status slot map and inventory icons

Goal: replace the remaining guessed status-bar icon placement with the field-by-field draw order from the mission HUD routine.

## ASM source

Main routine traced in `SAM1_unpacked_linear_8086.asm`:

- `SAM1:0x181F1..0x1849E` — normal bottom status bar draw path.
- `SAM1:0x1820B..0x1832C` — score conversion and six fixed score digits.
- `SAM1:0x18331..0x183AB` — ammo icon pair and two ammo digits.
- `SAM1:0x183B0..0x1845F` — speed/dynamite/key/floppy conditional icons.
- `SAM1:0x18464..0x1849E` — lives loop.

The routine uses `DS:6E32` as the HUD page pointer.  Sprite addresses are byte offsets from that page; because each SAM?02.GFX cell is `0x28` bytes after the three-byte header, the offset maps directly to a tile number.

## Slot map

All X positions below are status-bar 8px slots; pixel X is `slot * 8`.  Y is the bottom HUD row.

| ASM test / source | Destination slot | HUD tile | Runtime field |
|---|---:|---:|---|
| score digit 1..6 | `0x00..0x05` | digit tiles `0..9` | `score % 1000000` |
| fixed ammo icon left | `0x0C` | `12` | always drawn |
| fixed ammo icon right | `0x0D` | `10` | always drawn |
| ammo tens/ones | `0x0E..0x0F` | digit tiles `0..9` | `DS:6858`, clamped to 99 |
| `DS:69A4 > 0` | `0x14` | `13` | speed bonus active |
| `DS:69F4 != 0` | `0x19` | `20` | dynamite owned |
| `DS:69EA != 0` | `0x1B` | `17` | red key, raw `0x2D` |
| `DS:69EB != 0` | `0x1C` | `18` | blue key, raw `0x2F` |
| `DS:69E9 != 0` | `0x1D` | `19` | green key, raw `0x2B` |
| `DS:69EC != 0` | `0x1E` | `21` | floppy disk / laser computer item, raw `0x84` |
| lives loop `AX=1..DS:6A40` | `0x21..` | `11` | lives |

Important correction: raw `0x72` reveal glasses affect hidden-platform visibility, but this HUD routine does not draw a glasses icon.  The previous runtime HUD incorrectly reused tile 21 for glasses; tile 21 is the `DS:69EC` floppy/laser-computer item.

## Runtime changes

- Added the fixed two-cell ammo icon before the ammo digits.
- Moved speed/dynamite/keys/floppy to their exact ASM slots instead of packing them from the right side.
- Replaced the generic repeated key icon with the three color-specific key tiles and conditions.
- Mapped raw `0x84` / `has_floppy_disk` to tile 21 at slot `0x1E`.
- Removed the fake glasses HUD icon from the original-sprite path.
- Moved lives one slot right: first life is slot `0x21`, not `0x20`.
- Removed the fake death `00` overlay from the original-sprite path.

## Remaining UI gaps

The mission HUD slot map is now traced.  The remaining UI work is the broader menu/table/window renderer using `DS:6E36` and `DS:6E3A`, plus any special text control codes.
