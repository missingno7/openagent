# Pass 90 - teleporter re-exit guard and jump headroom gate

## Teleporter ASM recheck

Rechecked `SAM1:0xD48B..0xD5E8` and the timer branch at `SAM1:0x2014..0x2039`.

Findings:

- The `0x00B7` teleporter branch has no explicit test for the direction the player used to enter the pad.
- Rearming is blocked while `DS:69E0 != 0`.
- When armed, the branch sets `DS:69E2 = 0x13`.  The main loop decrements it every tick, copies `DS:69E4/DS:69E6` into player position when it reaches zero, and clears `DS:69E0` only at `DS:69E2 == -0x13`.
- The target X nudge is not based on player direction.  It probes runtime byte `+0x1CC` one row below the destination pad: non-zero nudges `+3`, zero nudges `-3`.

Runtime fix:

- The reconstructed runtime already kept a release gate after arrival, but it cleared it using full X/Y pad overlap.  If the player's Y was slightly outside the pad cell, the gate could clear while the player's X footprint was still inside the pad column.  Pressing the opposite direction could then step through the strict `+/-2 px` alignment band and warp back.
- The release gate now waits until the player's actual `B7D9` collision X footprint (`x+3..x+12`) has left the destination pad column.  This matches the intent of the ASM cooldown/nudge while compensating for the higher-level reconstructed interaction pass.

## Jump start headroom gate

Rechecked `SAM1:0xBC5E..0xBCB8` before the write to `DS:6EC1` at `0xBCED`.

The ordinary jump is not started immediately on `space && grounded`.  The EXE first probes body-solid byte `+0x1CC` at:

- `y - 3`, `x + 3`
- `y - 3`, `x + 12`

If either probe is solid, it jumps to the routine exit and does not write `DS:6EC1 = 1`, does not reset `DS:34EA`, and does not play the jump sound.  This prevents the player from initiating a jump into a solid tile directly above his head.

Runtime fix:

- Added `player_jump_headroom_clear()` and gate normal jump start with it.
