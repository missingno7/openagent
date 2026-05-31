# Pass 120 - raw 0xA7 barrel release and 0x51/0x52 launcher correction

This pass corrects two places where the previous reconstructed behaviour had
started to drift away from the ASM evidence and from in-game observation.

## Raw `0x51` / `0x52` stationary launchers

Pass 119 correctly traced the firing cadence and helper parameters, but it made
the wrong conclusion about the launcher body.  The older pass-29 hit-property
data was right: objects `0x01D0` / `0x01D1` are not in the decoded shot-damage
branches, and there is still no isolated ASM branch proving player-body contact
hurt or body solidity for those raw actors.

Current policy:

- `0x52` / object `0x01D0` / state `0x0A` is a right-facing timed launcher.
- `0x51` / object `0x01D1` / state `0x0B` is a left-facing timed launcher.
- `DS:34DA` remains an elapsed timer and fires immediately once charged and the
  row/front gate becomes true.
- The actor body is not a player contact hazard.
- The actor body is not a dynamic solid block for the player.
- Player shots should not be turned into body impacts merely because the object
  is absent from the damage table.

ASM still shows helper `0x5784` receiving `actor_y` for the projectile spawn:

- `0x52`: `x = actor_x + 8`, `y = actor_y`, direction `+1`, speed `4`, object `0x01D6`.
- `0x51`: `x = actor_x - 8`, `y = actor_y`, direction `-1`, speed `4`, object `0x01D6`.

The Python `Projectile.y` field is a logical/render anchor for ordinary
horizontal projectile sprites: the renderer draws them at `y - 7`.  To make the
visible projectile top match the EXE helper's `actor_y`, raw `0x51/0x52` now
store `actor_y + 7` in Python while documenting that the ASM parameter itself is
still `actor_y`.

## Raw `0xA7` barrel blocked-push release

The previous `release_barrel_against_wall()` implementation synthesized a
horizontal back-nudge when a player pushed the barrel into a wall.  The annotated
barrel branch does not currently support that: the decoded writes around
`SAM1:0x8335` and `SAM1:0x84B3` rewrite the actor to state `0x1389` and set
`DS:34DA = 0x10`; the following `0x1389` state subtracts `2` from `actor_y` and
runs a draw/cleanup transient, but no decoded instruction writes a horizontal
counter-step to `actor_x`.

Current policy:

- A blocked push flips the displayed barrel direction away from the push.
- The player/barrel collision enters a `0x10`-tick transient ignore window.
- The barrel is no longer nudged horizontally by the Python release helper.
- A successful horizontal push that moves the barrel past its last support pixel
  marks the barrel unsupported immediately; the actual vertical fall distance is
  still resolved by `update_barrels_tick()` / `move_barrel_vertical()`.

## Regression coverage

Updated checks:

- `tools/check_stationary_shooter_accuracy.py`
  - elapsed timer charges before line-of-sight;
  - charged launcher fires immediately when row/front gates become true;
  - left/right projectile X origins remain `actor_x +/- 8`;
  - rendered projectile top is compensated to the ASM `actor_y` helper param;
  - raw `0x51/0x52` body contact is harmless;
  - raw `0x51/0x52` body does not block player movement.
- `tools/check_barrel_player_interaction.py`
  - blocked push enters the release window without a horizontal side-pop.
- `tools/check_barrel_vertical_fall.py`
  - pushed-over-edge barrels are marked unsupported before the next fall tick.
