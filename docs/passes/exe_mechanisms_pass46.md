# Pass 46 — raw 0x24 / object 0x0065 / state 0x27 verification

This pass revisits raw `0x24`, the bank-2 two-high helmet enemy, against the
actual state `0x27` branch in `SAM1_unpacked_linear_8086.asm`.

Relevant EXE ranges:

- spawn/init: `SAM1:0x12CB2..0x12DC6`
- update: `SAM1:0xA89F..0xAFBF`
- projectile call: `SAM1:0xAAC3..0xAAED`

## Spawn fields

The raw token creates:

| field | value |
| --- | --- |
| object | `0x0065` |
| state | `0x27` |
| step | `2 px/tick` |
| shot timer period `DS:34D8` | `0x3C` / 60 ticks |
| shot timer `DS:34DA` | `0` |
| short/open timer `DS:34DC` | `3` initially |
| phase timer `DS:34DE` | `random(0x14) + 0x3C` = 60..79 |
| direction | random `+1` or `-1` |
| frame counter | `0xC9` when facing right, `0x01` when facing left |

The previous runtime initialized this as a generic shooter with its firing timer
already full.  That was not EXE-accurate: state `0x27` starts `DS:34DA` at zero.

## Movement / helmet phase

State `0x27` has two private phase counters:

- While `DS:34DE > 0`, the actor walks and accepts candidate X movement.
- When `DS:34DE` falls to `1`, the EXE sets `DS:34DC = 0x1E`.
- When `DS:34DE == 0`, the actor does not accept horizontal movement. It clamps
  the frame counter at the end of the directional range while `DS:34DC` counts
  down.
- When `DS:34DC` reaches zero, `DS:34DE` is refilled with `0x50` and walking
  resumes.

This explains why the enemy is not just a normal constantly-walking shooter: it
periodically stops in its helmet/open animation state.

## Frame counter ranges

This actor does not use the generic walker ranges.  The EXE initializes and
updates:

- facing left: `0x01..0x13`
- facing right: `0xC9..0xDB`

The renderer now compresses those ranges to the existing decoded bank-2
composite frames:

- top: `40..43`
- bottom: `44..47`

## Shooting

At `SAM1:0xAA31..0xAAED`, the branch increments `DS:34DA`.  Once it reaches
`DS:34D8` (`0x3C`), it resets the timer and checks:

1. `(player_y + 8) >> 4 == actor_y >> 4`
2. player is in the actor's facing direction:
   - actor facing right: `actor_x < player_x`
   - actor facing left: `actor_x > player_x`

If both pass, it calls helper `0x5784` with:

- X = actor X
- Y = actor Y
- direction = `DS:34E2`
- speed = `4`
- object = `0x033B`

Runtime now uses those direct actor coordinates instead of offsetting the shot by
`+8` Y / edge X like a generic guard.
