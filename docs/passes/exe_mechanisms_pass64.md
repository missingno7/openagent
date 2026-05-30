# Pass 64 — Projectile impact vs enemy hit refinement

Focus: player/enemy projectile follow-up effects.

## ASM cross-check

### Solid/wall impact drawing

The draw/update path around `SAM1:0x4EDD..0x4F94` treats projectile-like states
`0x07`, `0x0E`, `0x13` and transient state `0x1388` specially.  For those
states it marks the actor as drawn and calls the low-level draw/effect helper at
the projectile coordinates.  This is the path that visually reads as the bullet
impact/spark when the shot hits solid geometry.

### Enemy hit branch

The enemy/projectile hit branch around `SAM1:0x5C30..0x5C82` does something
separate: after `0x547C` confirms contact it plays sound `0x13`, adds score, and
rewrites the projectile actor slot to:

- `state = 0x1388`
- `object = 0x0187`
- `frame_counter = 1`
- `speed = 0`

However the enemy itself is already responsible for the visible hit reaction
through `DS:34CC = 3` white flash and/or its death/score transition.  The runtime
was drawing the full wall-impact spark over every enemy hit, which looked too
busy and did not match observed gameplay.

## Runtime changes

- Added `Projectile.impact_visible`.
- Solid tile / solid actor impacts still enter a visible impact state.
- Normal enemy hits now consume the player shot without drawing the big wall
  impact animation over the enemy.
- Hostile shots hitting the player now call the real `hurt_player()` helper
  instead of only setting a local flash/sound placeholder.
- Hostile shots are consumed on player hit without drawing a wall-impact spark
  on the player body.

Open question: object `0x0187` should still be decoded more narrowly against the
real draw table.  For now, the important gameplay/visual correction is that the
large visible spark is limited to solid impacts.
