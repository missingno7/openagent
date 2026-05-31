# Pass 122 - raw 0xA7 wall-contact release as state 0x1389

> **Superseded by pass 123.** This pass incorrectly mapped wall-blocked barrel pushing onto the destructive `0x00AA/state 0x1389` score branch. Keep it as audit history only; use pass 123 and the current registries for implementation truth.

This pass treats player observations as testcases rather than truth and rechecks
`release_barrel_against_wall()` against the decoded `SAM1` branch.

## ASM evidence

The relevant raw-barrel actor range is still `SAM1:0x82E3..0x8742`.

Two distinct paths matter:

1. `SAM1:0x82F2..0x8335` calls helper `0x547C` at the actor coordinates.  A
   focused read of `0x547C` shows it iterates the player projectile slots
   (`DS:683C/683E`, flags around `DS:6858/6859`) and returns whether a shot
   overlaps the queried actor rectangle.  This is not the wall-blocked player
   push path.
2. `SAM1:0x83C4..0x848A` is the player/barrel overlap path.  After the already
   implemented `x+3..x+12`, `y..y+15` overlap test succeeds, `0x848A..0x84E9`:
   - plays sound `0x04`,
   - adds `0x03E8` to the score accumulator,
   - sets `DS:34E8 = 0x1389`,
   - sets `DS:34DA = 0x10`,
   - sets visible object `DS:34E0 = 0x00AA`,
   - sets frame `DS:34D6 = 1`,
   - clears speed `DS:34E6 = 0`.

The following state branch `SAM1:0x8542..0x8742` stores previous/current draw
coordinates, subtracts `2` from actor Y each actor tick, clamps Y to absolute
`0x10`, decrements `DS:34DA`, and marks the slot inactive through `DS:34EB=1`
when the timer expires.

Critically, this decoded path does **not** write actor X (`DS:34CE`) and does
**not** write actor direction (`DS:34E2/34E4`).  Therefore the port must not
model the release as a horizontal pop or forced direction flip.

## Runtime change

`release_barrel_against_wall()` now maps the wall-blocked push case onto the
ASM player-contact rewrite instead of a hand-made pass-through flag:

- `barrel.code = 0xAA`
- `barrel.behavior_state = 0x1389`
- `barrel.transient_ticks = 0x10`
- player/barrel collision treats this state as pass-through
- score `+0x03E8` and sound `0x04` are emitted when the rewrite happens
- `update_barrel_1389_transient()` moves the actor upward by `2 px/tick`, clamps
  at `0x10`, and removes the actor after the timer expires

The existing successful-push path is intentionally separate: pushing the barrel
left/right still moves raw `0xA7` through broad barrel-vs-world body collision,
and the pushed-off-edge unsupported marker remains a partial approximation until
there is a DOSBox trace.

## What this means for the observation

The observation that the barrel becomes pass-through when pressed into a wall is
consistent with the ASM: it is no longer a normal `0xA7` body once the player
contact rewrite happens.  The apparent “jump” should **not** be implemented as a
sideways snap, because the decoded state writes only Y/timer/object state, not X.

## Regression coverage

`tools/check_barrel_player_interaction.py` now checks that a blocked side push:

- keeps actor X unchanged,
- keeps direction unchanged,
- rewrites to object `0xAA/state 0x1389`,
- starts a `0x10` timer,
- awards `0x03E8`,
- plays sound `0x04`,
- leaves the actor pass-through,
- advances upward for the transient and removes the actor when the timer expires.
