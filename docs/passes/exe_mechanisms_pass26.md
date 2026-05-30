# Pass 26 - stationary shooter trap actors

This pass continues moving mechanics from static map rendering into the EXE actor
model.  The new target is the group of stationary shooter objects initialized by
the special actor table at `CS:3A59` and updated by the dispatcher around
`SAM1:0x6B74..0x6D47`.

## Actor table entries

| raw | object id | state | direction | timer |
|---:|---:|---:|---|---|
| `0x52` | `0x01D0` | `0x0A` | right | `random(20)+55` |
| `0x51` | `0x01D1` | `0x0B` | left | `random(20)+55` |
| `0x3C` | `0x01E7` | `0x0C` | right | `random(20)+55` |
| `0x3D` | `0x01EB` | `0x0D` | left | `random(20)+55` |

The EXE branch increments `DS:34DA`, compares it against `DS:34D8`, then checks
that `(player_y + 8) & 0xfff0` equals `actor_y & 0xfff0`.  It also checks that
the player is in front of the emitter before calling projectile helper `0x5784`.
This means these are not passive decorative tiles and should not be baked into
the static background.

## Projectile helper calls

For states `0x0A/0x0B`, the helper receives object id `0x01D6`, direction
`+1/-1`, speed `4`, and an x offset of `+8/-8`.

For states `0x0C/0x0D`, the helper receives `0x01E8/0x01EC`, direction `+1/-1`,
speed `4`, and an x offset of `+16/-16`.

The decoded sprites used in the prototype are therefore:

- `0x01D6` -> bank 4 tile 19.
- `0x01E8` -> bank 4 tile 37.
- `0x01EC` -> bank 4 tile 41.

## Runtime changes

- Added `STATIONARY_SHOOTER_CODES = {0x52,0x51,0x3C,0x3D}` and included them in
  dynamic mission codes so their raw marker is not drawn statically.
- Spawned these as runtime `Enemy(kind="stationary_shooter")` actors with zero
  movement and EXE-derived direction/timer.
- Added a stationary branch in `update_entities_tick()` that only counts down
  and fires when the same-row/front-facing gate is satisfied.
- Added projectile sprite selection for these traps, separate from player/bank14
  guard bullets.

Open issue: the full projectile actor state machine after helper `0x5784` is
still only partially modelled.  Speed and sprite family are now EXE-derived, but
collision side effects beyond damaging the player still need a separate pass.
