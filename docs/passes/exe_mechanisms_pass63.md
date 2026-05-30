# Pass 63 — raw 0x4D landmine touch/death timing audit

This pass rechecked the landmine path against the unpacked SAM1 assembly because
the runtime behaviour felt too delayed compared with the original game.

## Confirmed ASM paths

### Player touches idle mine object `0x0270`

Interaction dispatcher branch:

- `SAM1:0xD0B1` checks `AX == 0x0270`.
- `SAM1:0xD0F6` clears the map/runtime cell at `0x1CA`.
- `SAM1:0xD110` writes actor object `0x0271`.
- `SAM1:0xD18F` sets `DS:34D6 = 1`.
- `SAM1:0xD1A9` sets `DS:34D8 = 0x28`.
- `SAM1:0xD1C3` sets state `DS:34E8 = 0x17`.
- `SAM1:0xD1ED..0xD205` sets player death state `DS:69F5 = 1`, `DS:69F6 = 0x23`, unless protection flag `DS:69F3` is active.

Important consequence: stepping on the idle mine kills immediately in the same
interaction branch.  The state-`0x17` explosion update is not the first moment
when the player is supposed to die.

### State `0x17` update after the mine is armed

Update dispatcher branch:

- `SAM1:0x7782..0x78C1` is state `0x17`.
- It increments `DS:34D6` every actor tick.
- At `DS:34D6 == 0x0B`, it calls helper `0x53C4`, the player contact hazard check.
- For object `0x0271`, once `DS:34D6 > 0x0B`, it draws/clears a small explosion column around the mine.
- For non-`0x0271` objects in this state, it wraps `DS:34D6` after frame `9`.

Runtime consequence: frame `0x0B` remains a secondary explosion/contact hard-death
check, but normal stepping on raw `0x4D` no longer waits for that frame.

### Idle visual timing

Draw dispatcher branches:

- `SAM1:0x36C2..0x3725` draws object family `0x0259..0x0270` using `floor(DS:34D6 / 5)`.
- `SAM1:0x3728..0x378E` draws object `0x0271` using `floor(DS:34D6 / 3)`.

For idle object `0x0270`, the runtime now wraps `DS:34D6` after `9`, so the idle
mine is exactly a two-frame blink:

- frames `1..4` -> first cel
- frames `5..9` -> second cel

## Runtime changes

- Touching idle raw `0x4D` now immediately calls `kill_player()` after spawning the
  triggered object `0x0271/state 0x17` and clearing the source cell.
- The delayed frame-`0x0B` death check remains for the armed explosion actor.
- Idle mine animation timing now matches `floor(DS:34D6 / 5)` and wraps after `9`.
- Triggered mine visual timing now uses `floor(DS:34D6 / 3)`.
