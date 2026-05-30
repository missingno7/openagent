# Pass 47 — raw 0x24 helmet vulnerability

This pass revisits the player-shot damage path for raw `0x24`, not just its
movement/shooting update.

Relevant ranges in `dissassembly/SAM1_unpacked_linear_8086.asm`:

- hit dispatcher object-id branch: `SAM1:0x4E74..0x4ED2`
- state `0x27` update/death branch: `SAM1:0xAE8E..0xAFBF`

## What the EXE shows

The hit dispatcher has a dedicated object branch for `0x0065`, the object used
by raw `0x24`.  Unlike the generic `0x0321..0x0383` two-high enemies, this branch
places the shot impact only around `actor_y - 0x10`, i.e. the top/helmet tile.

The actual state `0x27` update later checks `DS:34DE`:

- if `DS:34DE != 0`, the actor is still in the walking/helmet-on phase; the EXE
  only plays sound `0x08` and does not enter the death/score branch;
- if `DS:34DE == 0`, the actor is in the stopped/open phase; the branch awards
  `0x03E8` points, marks the actor hit/dead, draws the explosion points around
  the two-tile sprite, and calls the score-popup helper.

So the enemy is shootable only while the helmet is open/off.  This matches the
visual gameplay observation that hits during the closed helmet phase should not
kill it.

## Runtime change

`hit_enemy_with_projectile()` now special-cases `enemy.kind == "state27_shooter"`:

- closed/walking phase (`phase_ticks > 0`): no HP loss, no removal, hurt/ping
  sound only;
- open/stopped phase (`phase_ticks <= 0`): immediate kill, +1000 score, score
  popup, impact effect, enemy-death sound.

This replaces the previous generic `hp=3` behaviour for raw `0x24`.
