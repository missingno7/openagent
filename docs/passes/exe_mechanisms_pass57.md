# EXE mechanisms pass 57 — sound rollback, HUD audit, player death animation

## 1. PC speaker sound synthesis

Pass 56 changed the decoded `.SND` words to `1193182 / value` as if every word
were a raw PIT divisor.  That made gameplay effects, especially jump, sound
visibly worse.  Re-checking the existing Secret Agent/OpenCrystalCaves sound
format notes shows the safer model is the original 610-byte record player:

- 300 signed words, terminated by `-1`;
- 320 samples per word at 44.1 kHz;
- `vibrate` gates which words produce sound;
- the word is consumed directly as the square-wave pitch value.

Runtime change: `openagent.sound.synthesize_sound()` is reverted to direct pitch
words.  The one-based EXE sound-id dispatch remains unchanged (`id 1 -> record 0`).

## 2. HUD/status strip audit

The 8px height from pass 56 is still correct, but the art in the runtime is not
yet the original art.  The ASM makes that very clear: the status routine does not
use Python/system fonts and does not use arbitrary hand-drawn icons.  It blits
8x8 cells from a table pointed to by `DS:6E32`.  Each cell is `0x28` bytes, which
matches an 8-row masked EGA cell: `8 rows * 1 byte-cell * 5 planes`.

Important anchors in `SAM1:0x181F1..0x1872A`:

- score is formatted to six chars from `DS:699A/DS:699C`; spaces are changed to
  ASCII `0x30`;
- digit sprite address: `(ascii_digit - 0x2F) * 0x28 + DS:6E32 - 0x25`;
- ammo digits use the same digit cells from `DS:6858`;
- static separators/icons use fixed offsets from `DS:6E32`;
- inventory/status icons are conditional on `DS:69F4`, `DS:69EA`, `DS:69EB`,
  `DS:69E9`, `DS:69EC`;
- lives loop uses `DS:6A40` and offset `DS:6E32 + 0x01BB`.

Recovered draw slots from the phase-0 path:

| Item | Source | DS:6E32 offset | X slot |
|---|---|---:|---:|
| score digit 1..6 | `DS:699A/699C` formatted | digit formula | `0..5` |
| score separator/static glyph | fixed | `0x01E3` | `0x0C` |
| ammo icon/static glyph | fixed | `0x0193` | `0x0D` |
| ammo tens/ones | `DS:6858` | digit formula | `0x0E`, `0x0F` |
| extra-speed/status | `DS:69A4 > 0` | `0x020B` | `0x14` |
| flag icon | `DS:69F4` | `0x0323` | `0x19` |
| flag icon | `DS:69EA` | `0x02AB` | `0x1B` |
| flag icon | `DS:69EB` | `0x02D3` | `0x1C` |
| flag icon | `DS:69E9` | `0x02FB` | `0x1D` |
| flag icon | `DS:69EC` | `0x034B` | `0x1E` |
| life icons | `DS:6A40` loop | `0x01BB` | `life_index << 3 + 0x100` in phase path |

Runtime change in this pass is conservative: comments now mark the current masks
as temporary, not original art.  The next required task is to trace the loader
that fills `DS:6E32` (`SAM1:0x1BBE5..0x1BC10`) and decode that 0x800-byte block.

## 3. Player death animation

The original does not freeze the game immediately when a hard-death branch fires.
Hard death sets:

```asm
DS:69F5 = 1
DS:69F6 = 0x23
```

Then the player state/update path at `SAM1:0x1A21..0x1ABC` continues running the
countdown.  The draw table identifies bank-13 tiles `14,15` as the two death
cel frames.

Runtime change:

- `kill_player()` starts a `0x23`-tick death countdown;
- while the countdown is active, movement/input stays stopped but rendering still
  draws the player;
- the player sprite alternates bank 13 tiles `14` and `15`;
- respawn happens only after the countdown finishes.
