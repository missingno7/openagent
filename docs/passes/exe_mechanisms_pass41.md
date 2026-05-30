# Pass 41 — state 0x21 ceiling laser verification

This pass re-checks raw `0x63` against the SAM1 disassembly instead of relying on the earlier visual/gameplay approximation.

## Correct state branch

Raw `0x63` is initialized by the special actor table path at `SAM1:0x1251e..0x12560`:

- `DS:34E6 = 2` horizontal step
- `DS:34D8 = random(0x14) + 0x1e` period
- `DS:34DA = 0` timer
- `DS:34DC = 3`
- `DS:34E8 = 0x21`

The earlier notes that used `SAM1:0x63c0..0x6455` for this enemy were wrong for raw `0x63`; that block is a horizontal shooter branch.  The state `0x21` branch is at `SAM1:0x98d9..0x9ab6`.

## Movement / edge behaviour

`SAM1:0x98e1..0x99cd` probes the collision table for the candidate actor position before accepting the horizontal step.  If the probe fails, the EXE negates `DS:34E2` and resets the walk frame (`DS:34D6` to `0x01` or `0x15` depending on direction).  Runtime now checks the candidate ceiling-track support instead of the already-accepted old position, so the crawler does not overshoot past the last block above it.

## Firing gate and projectile

`SAM1:0x9a25` increments `DS:34DA` and compares it to `DS:34D8`.  When the period is reached, `SAM1:0x9a48..0x9a78` checks:

- player X is within approximately actor_x ± 16 px;
- player Y is below the crawler.

If the check passes, `SAM1:0x9a83` resets `DS:34DA = 0` and `SAM1:0x9aa6` calls projectile helper `0x5784` with:

- `object = 0x00c7`
- `speed = 8`
- `direction = 1`
- spawn Y = actor_y + 8

The helper rewrites `object 0x00c7` to `object 0x72`, `state 0x89`.  The runtime represents this with the decoded vertical laser family `bank 2 tiles 13..15`.

If the period is reached but the player is not under the crawler, `SAM1:0x9ab2` decrements `DS:34DA`, leaving it at `period-1`.  That means after the enemy has armed, walking under it fires on the next actor tick rather than waiting a full new cooldown.
