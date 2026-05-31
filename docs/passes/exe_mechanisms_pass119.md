# Pass 119 - raw 0x51/0x52 stationary launcher tick accuracy

This pass re-audits the raw `0x52` / `0x51` stationary enemy launchers after an
in-game mismatch report around firing cadence.  Its cadence/origin findings are
kept, but its body-solid/contact conclusion is superseded by pass 120.

## ASM anchors

The relevant actor states are dispatched at `SAM1:0x6B74..0x6D47`:

| raw | object | state | facing | branch |
|---:|---:|---:|---|---|
| `0x52` | `0x01D0` | `0x0A` | right | `SAM1:0x6B74..0x6C5C` |
| `0x51` | `0x01D1` | `0x0B` | left | `SAM1:0x6C5F..0x6D47` |

Important tick details:

- `SAM1:0x6B88` and `SAM1:0x6C73` increment `DS:34DA` before doing any player
  row/facing gate.
- `SAM1:0x6B9E` and `SAM1:0x6C89` compare that elapsed timer to `DS:34D8`.
- The timer is reset to zero only after all gates pass:
  - right-facing `0x52`: `SAM1:0x6BF2..0x6BF4`
  - left-facing `0x51`: `SAM1:0x6CDD..0x6CDF`
- The row gate compares `(player_y + 8) & 0xfff0` with `actor_y & 0xfff0`.
- The facing gate is strict:
  - `0x52`: `actor_x < player_x`
  - `0x51`: `actor_x > player_x`
- Projectile helper `0x5784` receives object `0x01D6`, speed `4`, and:
  - `0x52`: `x = actor_x + 8`, `y = actor_y`, direction `+1`
  - `0x51`: `x = actor_x - 8`, `y = actor_y`, direction `-1`

## Fixes

- `Enemy.shoot_timer_ticks` for stationary launchers now starts at `0`, because
  it models EXE `DS:34DA` as an elapsed timer, not a countdown-to-zero.
- The update branch increments/caps the timer every actor tick while the launcher
  is active.  It does not wait for the player to already be in the same row.
- A charged launcher now fires immediately on the first tick where row and facing
  gates become true, then resets to `0`.
- Raw `0x51/0x52` projectile spawn now uses `actor_y` directly instead of the
  previous `actor_y + 8` approximation.
- SUPERSEDED BY PASS 120: this pass briefly treated stationary launcher bodies
  as indestructible solid contact hazards.  That was not supported by the decoded
  damage/contact branches; raw `0x51/0x52` are now non-solid and harmless on body
  contact.

## Remaining gap

The firing branch is directly ASM-traced.  The body-contact part of this pass is
superseded by pass 120, which removes the unsupported solid/contact-hazard
implementation for object `0x01D0/0x01D1`.

## Regression

Added `tools/check_stationary_shooter_accuracy.py`, covering:

- elapsed timer charging while the player is not in the same row;
- immediate firing after the row/facing gate becomes true;
- left-facing `0x51` front gate and `x-8` projectile origin;
- SUPERSEDED in pass 120: body contact and body blocking checks now assert the
  opposite policy, because raw `0x51/0x52` should not be solid or harmful by
  touch.


## Correction in pass 120

The firing cadence and helper origin analysis above remain useful, but the pass
119 body-policy conclusion was wrong.  Pass 120 removes the unsupported solid
contact-hazard treatment for raw `0x51/0x52`; these actors are non-solid and do
not hurt the player by body contact.  Their threat comes from projectile
`0x01D6`.  Pass 120 also documents why Python stores projectile `y = actor_y+7`
for rendering even though helper `0x5784` receives `actor_y` in ASM.
