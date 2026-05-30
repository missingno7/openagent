# Pass 65 — ammo count init/cap and pickup branch audit

Focus: another small but real systemic gameplay mismatch around player shots.

## ASM evidence

The player fire path reads the global ammo word at `DS:6858`.  The new-game/init
path sets it to five shots:

- `SAM1:0x28CE1`: `movw $0x5,0x6858`
- the same init pattern is repeated in the other episode/start branches.

The extra-shots pickup branch is the runtime visual `0x012D` path:

- raw map code `0x73` generates runtime visual/object `0x012D` in the decoded
  collision/runtime table;
- `SAM1:0xC0BF..0xC0C5` adds `+5` to `DS:6858`;
- `SAM1:0xC0EF..0xC0FC` clamps it to `0x63`, i.e. 99 shots;
- `SAM1:0xC102..0xC106` plays sound `0x05` after clearing the cell.

## Runtime fixes

- Added `STARTING_AMMO = 5` and `MAX_AMMO = 0x63`.
- Runtime now starts/reset-loads mission playtest with five shots instead of
  zero.
- Raw `0x73` extra-shots pickup now clamps ammo to 99 instead of growing
  without limit.
- HUD ammo rendering uses the same 99 cap.

This keeps the pass narrow: it does not change the previously-audited fire/no
ammo sound IDs (`0x02` for fire, `0x14` for denied/no-ammo, `0x05` for ammo
pickup).
