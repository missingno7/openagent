# Pass 80 - normal mission player tick audit

## Scope

This pass rechecks the ordinary platformer movement path against SAM1. It keeps
the normal jump separate from the older `DS:69F5/DS:69F6` bounce/death path.

## Horizontal movement

- `SAM1:0x532D..0x53C0` increments held-direction counter `DS:681E`.
- With normal `DS:69B0 = 0`, `DS:69A4 = 4`, the per-tick steps are:
  `1, 1, 2, 4, 4, 4, 8...`.
- `SAM1:0x084B..0x0869` resets the counter only after all movement directions
  are released.
- `SAM1:0xB7D9..0xB8A4` also resets it after a blocked collision.

The runtime no longer restarts acceleration merely because left/right direction
changed, and it now resets the counter after a blocked horizontal move.

## Normal jump and fall

- `SAM1:0xBCED..0xBCF7` starts a jump with `DS:6EC1 = 1`, `DS:34EA = 0`.
- `SAM1:0xBD06..0xBD7E` increments `DS:34EA` and subtracts
  `byte[DS:34AF + DS:34EA]` from player Y.
- On the apex tick, `DS:34EA == 0x0A`, the EXE clears `DS:6EC1`, rewinds the
  counter to `9`, and still moves upward by `table[9] = 1` in that same tick.
- `SAM1:0xB8B3..0xBA49` handles falling with the same table, incrementing and
  capping the counter at `0x13`.

The runtime previously skipped the one-pixel apex move. Tick transitions now
live in `openagent/player_motion.py`, and upward motion uses one atomic collision
probe per DOS tick like `SAM1:0xBD22..0xBD80`.

## Normal jump animation state

The ordinary `DS:6EC1` jump uses directional player states `0x0D/0x0E`, selected
at `SAM1:0xBCBA..0xBCE4`. Alternating states `0x0F/0x10` belong to the separate
`DS:69F5/DS:69F6` bounce/death-style path at `SAM1:0x1A77..0x1A8C`.

The decoded atlas maps both pairs onto the same two air-looking cels, so the old
runtime looked plausible while carrying the wrong internal state. It now uses
`0x0D/0x0E` for a normal mission jump.

## Remaining gaps

- Normal horizontal map collision was switched to an atomic destination probe
  in pass 82. Pushable-barrel overlap remains a separate reconstructed fallback.
- Ladder/direct vertical movement flags `DS:6EC3/DS:6EC4` remain unimplemented.
- Difficulty modifiers `DS:69B0/DS:69A4` beyond the normal path remain
  unimplemented.
