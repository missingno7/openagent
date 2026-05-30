# Pass 43 - remaining special-table animated states

This pass continues filling the non-enemy entries from the SAM1 special actor
table at `CS:3A59` and the actor dispatcher around `SAM1:0xB599..0xB65D`.

## raw `0x40` / object `0x0131` / state `0x2B`

The parser branch at `SAM1:0x13CC1..0x13DE4` creates an actor slot with:

- `DS:34E0 = 0x0131`
- `DS:34D6 = random(0x12) + 1`
- `DS:34DA = 5`
- `DS:34E8 = 0x2B`

The update branch at `SAM1:0xB599..0xB5FC` increments `DS:34D8` until it equals
`DS:34DA`, then advances `DS:34D6`.  If the frame counter passes `0x13`, it is
reset to `random(5)+1`.

Runtime now extracts raw `0x40` as a dynamic `state2b_anim` actor instead of
baking only the raw map cel into the static layer.

## raw `0xD4` / object `0x0135` / state `0x2C`

The parser branch at `SAM1:0x13DEB..0x13F04` creates:

- `DS:34E0 = 0x0135`
- `DS:34D6 = 1`
- `DS:34DA = 2`
- `DS:34E8 = 0x2C`

The shared state `0x2C` update at `SAM1:0xB5FE..0xB65D` advances the animation
counter and wraps values above `0x13` back to `1`.

Runtime now extracts raw `0xD4` as a dynamic `state2c_anim` actor.

## raw `0x78` / object `0x0103` / state `0x2C`

The parser branch at `SAM1:0x13F0A..0x14023` creates the same state `0x2C`
actor but with `DS:34E0 = 0x0103`.  In the `0x2C` branch, object `0x0103`
gets a special extra call:

- `SAM1:0xB615` compares object id with `0x0103`.
- If equal, it increments `DS:34D6` a second time and calls helper `0x53C4`
  with actor X/Y.
- Helper `0x53C4` is a narrow player-overlap hazard path: it compares the
  player position against roughly a 10x16 rectangle and sets the player hurt /
  death flags depending on protection state.

Runtime now treats raw `0x78` as the dynamic state `0x2C` animated hazard and
applies contact damage on overlap.

## Implementation notes

- Added `ANIMATED_SPECIAL_CODES = {0x40, 0xD4, 0x78}` to the dynamic-code set, so
  these raw cells are skipped from the static render/collision source layer and
  redrawn as actor slots.
- Added deterministic frame initialization for raw `0x40` to mirror the EXE's
  random initial `DS:34D6` while keeping editor playback reproducible.
- The visual mapping uses the decoded atlas families currently associated with
  the raw map codes: `0x40` and `0xD4` in bank 9, `0x78` in bank 15.
