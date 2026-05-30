# Pass 79 - cleanup regression fix and player hurt flash

## Combat extraction regression

Pass 74 moved projectile hit policy into `openagent/combat.py`, but the extracted
module still called `actor_walk_counter_next()` without importing it. Shooting a
bank-14 guard therefore raised `NameError`.

`combat.py` now imports the helper from `openagent.animation`.

## Player hurt visual

The generic player-damage path already modeled the `0x1E`-tick invulnerability
window, but did not render its original bright pulses.

ASM anchors:

- `SAM1:0x5437..0x5455` starts `DS:6A41 = 1`, `DS:6A42 = 0x1E`.
- `SAM1:0x20F8..0x216F` decrements `DS:6A42` in the player draw path.
- The same draw path starts a five-pass bright render at the beginning and
  restarts it when the remaining counter reaches `0x14` and `0x0A`.

The runtime now derives those three white pulse windows from `hurt_flash` and
applies them only to the mission player sprite. Hard-death animation and the
overworld icon remain separate paths.
