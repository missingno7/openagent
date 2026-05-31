# Pass 115 - raw `0x40` state-`0x2B` decorative object correction

This pass re-audits raw `0x40` / object `0x0131` / state `0x2B` after playtesting showed two mismatches:

- touching it hurt the player in the port, but not in the original game;
- the lower cel was drawn with the wrong decoded tile.

## ASM evidence

### Spawn/parser

The raw-`0x40` parser branch at `SAM1:0x13CC1..0x13DE4` creates an actor slot with:

- `DS:34E0 = 0x0131`
- `DS:34CE = map_x << 4`
- `DS:34D0 = (map_y - 1) << 4`
- `DS:34D6 = random(0x12) + 1`
- `DS:34DA = 5`
- `DS:34E8 = 0x2B`

That confirms the actor origin is one tile below the animated upper cel.

### Update/contact

The update branch at `SAM1:0xB599..0xB5FC` only increments the private timer/frame fields:

- increment `DS:34D8`
- when it reaches `DS:34DA`, increment `DS:34D6`
- when `DS:34D6 > 0x13`, reset to `random(5)+1`
- clear `DS:34D8`

There is no call to helper `0x53C4` in the state-`0x2B` branch.  The explicit contact helper appears in the neighbouring state-`0x2C` branch only for object `0x0103` at `SAM1:0xB615..0xB63F`.

### Render family

Object `0x0131` falls into the object renderer range `0x12D..0x15E` at `SAM1:0x2649..0x26AB`.  The renderer uses:

```text
visual_index = (DS:34E0 - 0x012C) + floor(DS:34D6 / 5)
source_page  = DS:6DA2
```

Together with the raw map composite, this keeps the lower cel as bank 9 tile 1 while the upper cel animates through the bank 9 4..7 family.

## Runtime changes

- `state2b_actor_refs()` now draws the lower cel as bank 9 tile 1 instead of bank 9 tile 8.
- The broad generic `check_enemy_touch()` path skips `state2b_anim` actors.
- The same broad path also skips `state2c_anim` actors; state `0x2C` damage must come only from its explicit object-specific `0x53C4` branch, not from broad sprite overlap.
- Added `tools/check_state2b_decorative.py` and included it in `tools/check_handoff.py`.

## Still open

The exact decoded object-family source page mapping should eventually be generated from the object renderer ranges instead of represented by hand-written bank/tile refs.
