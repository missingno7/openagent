# Pass 92 — player hard-death bounce and level restart

This pass rechecked the `DS:69F5/DS:69F6` path because the Python runtime still
behaved like a frozen countdown: the player stopped in place, the rest of the
mission stopped updating, and the end of the timer only respawned the player on
the mutated level.

## Confirmed ASM behavior

Hard-death callers set:

```asm
DS:69F5 = 1
DS:69F6 = 0x23
```

The player update path at `SAM1:0x1A61..0x1AE8` then continues to run every DOS
tick:

```asm
1a61: cmpb $0x0, DS:69F5
1a6b: copy DS:34EE/34F0 into previous-position globals DS:34F2/34F4
1a77: toggle DS:3500 between 0x0F and 0x10
1a8c: if DS:69F6 == 0x23, play sound 0x16
1a9c: dec DS:69F6
1aa0: if DS:69F6 == 0, call restart/transition helper 0x520:0x011A
1ab3: AL = DS:69F6
1aba: DI = AL << 1
1abc: AX = word [DS:69F6 + DI]
1ac0: DS:34F0 -= AX
```

The displacement table is the same signed table documented in pass 10:

```text
index 1..12  = -8
index 13..18 = -6
index 19..22 = -4
index 23..25 = 0
index 26..27 = 4
index 28..35 = 8
```

Because the routine subtracts the signed value from Y, the high positive indexes
throw the player upward first, then the zero/negative values make him fall down.
Index 0 is not a motion step: when the decremented timer reaches zero the EXE
calls the restart helper before applying another displacement.

## Runtime changes

- Added `PLAYER_DEATH_TIMER_INITIAL` and `PLAYER_DEATH_BOUNCE_STEP_TABLE`.
- Added `advance_death_bounce_tick()` as a pure tick helper in
  `openagent/player_motion.py`.
- `update_player_death()` now advances the death arc on the DOS tick clock and
  applies `player.y -= signed_step` without normal collision.
- The main tick loop keeps updating entities, animated hazards, projectiles,
  explosions and door-blast timers while the player is dead. Only normal player
  input/movement/interactions are gated.
- When the death timer reaches zero, the runtime resets the current mission
  state instead of only respawning the player into the already-mutated level.
  The game-over/menu path is still not reconstructed; if lives reaches zero, it
  refills to three for playtesting.

## Remaining gaps

- The exact restart helper at `0x520:0x011A` should still be traced to confirm
  what score/ammo/inventory fields persist after a life loss.
- The death draw currently uses the decoded bank-13 two-cel death pair. The ASM
  toggles `DS:3500` between `0x0F/0x10`, and the renderer mapping should be kept
  under visual comparison against DOSBox captures.
