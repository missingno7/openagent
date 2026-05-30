# EXE mechanisms pass 89 — raw `0x58` / object `0x0331` / state `0x1F`

Re-audited raw mission code `0x58` after the old runtime showed the wrong
bank-12 cels and treated the actor as a continuously walking shooter.

## ASM evidence

- Spawn/init at `SAM1:0x120EA..0x121FE` creates object `0x0331`, state `0x1F`:
  - `DS:34E6 = 2` px/tick,
  - `DS:34D8 = 0x3C`, `DS:34DA = 0`,
  - `DS:34DC = 3`,
  - `DS:34DE = random(0x14) + 0x3C`,
  - direction is random; frame counter is `0x3D` for direction `+1` and `0x01` for direction `-1`.
- Runtime branch `SAM1:0x905C..0x977A`:
  - does side/floor probes for the two-high actor,
  - reverses direction and resets `DS:34D6` to the matching direction range when blocked,
  - increments `DS:34DA` to `DS:34D8` and fires object `0x033B` with speed `4` only if the player is on the same row and in the facing direction,
  - uses `DS:34DE` as the walking phase; when it expires the actor stops, sets `DS:34DC = 0x1E`, advances/clamps animation frames, and restarts walking with `DS:34DE = 0x50`.

## Sprite mapping

Raw `0x58` is a vertical two-tile composite in bank 12, not the old `31..38`
approximation and not a mirrored one-direction sprite:

- moving/facing left: top `16..19`, bottom `20..23`,
- moving/facing right: top `28..31`, bottom `32..35`.

The render path now draws those explicit top/bottom ranges and does not flip
`0x58` horizontally.

## Runtime changes

- Added state-`0x1F` frame helpers in `openagent/animation.py`.
- Spawn now initializes `0x58` frame counter, `DA/DC/DE` timers, and shot timer
  from the same ASM fields as the EXE.
- `runtime.py` now has a dedicated `state1f_shooter` tick branch instead of
  letting `0x58` fall through the generic walker/shooter path.
- Player contact is still handled as a two-high actor contact hazard through
  the shared actor rectangle.
