# Pass 48 — raw 0x24 HP / aux field audit

This pass checks whether raw `0x24` / object `0x0065` should also have a
normal hit-point counter.

## Evidence

The spawn/init block at `SAM1:0x12BD5..0x12DC6` does write:

- `DS:34DC = 3` at `SAM1:0x12DA0`,
- `DS:34DE = random(0x14) + 0x3C`,
- `DS:34E8 = 0x27`.

At first sight this looks like the same `aux_dc = 3` hint used by some larger
actors.  However, the state-`0x27` update later reuses `DS:34DC` as a phase
countdown:

- when `DS:34DE == 1`, the EXE writes `DS:34DC = 0x1E`,
- while `DS:34DE == 0`, it decrements `DS:34DC`,
- when `DS:34DC` reaches zero, it refills `DS:34DE = 0x50`.

So for this actor, `DS:34DC` is not a stable HP counter.  It is a timer for the
helmet-open/stopped phase.

The projectile overlap helper `0x547C` is called by state `0x27`, but the
observed branch does not decrement a separate `3 -> 2 -> 1 -> 0` HP value for
object `0x0065`.  The earlier runtime entry `ACTOR_HP_BY_OBJECT_ID[0x0065] = 3`
was therefore misleading.

## Runtime change

- Removed `0x0065: 3` from the generic object HP hint table.
- Kept raw `0x24` on the dedicated `state27_shooter` damage path.
- Closed helmet phase remains invulnerable.
- Open/stopped phase remains the vulnerable phase; no generic 3-HP counter is
  applied unless a future disassembly pass finds a separate decrementing field.

## Current conclusion

Raw `0x24` has a field initialized to `3`, but in this state it is not reliable
evidence of 3 HP.  The best current model is phase-gated vulnerability, not
normal multi-HP durability.
