# Pass 31 — ceiling laser crawler, push barrel edge case, beam-core animation, shark swimmer

This pass corrects several mechanics that were previously implemented too visually rather than from actor-state behavior.

## Ceiling laser crawler (`raw 0x63`, bank 12 tiles `36..43`)

The `0x63` actor remains mapped to object id `0x0345`, state `0x21`, speed `2 px/tick`, and a `random(20)+30` style timer range from the extracted special actor table.

The important correction is the firing gate:

- it is an actor, not a passive animated tile;
- the actor must be inside the standard active 320×200 gameplay viewport;
- it checks whether the player is underneath its column, not whether the modern resized window happens to show it;
- when the player enters the column underneath it, it emits the vertical projectile/laser family immediately, then uses the timer as cooldown.

The decoded vertical laser projectile is represented by bank 2 tiles `13..15`.  The runtime now animates that projectile family while it moves downward at `8 px/tick`.

## Pushable barrel (`raw 0xA7`, bank 6 tile `24`)

The previous implementation stopped the player when a barrel was pushed into a wall.  In the original game the player is not trapped there: the barrel turns/gets nudged away from the wall and the player can overlap/pass through for that tick.

The runtime now mirrors that behavior more closely:

- normal push: barrel moves in the player push direction;
- blocked push: barrel direction flips, the barrel is nudged one pixel away from the wall, and the player collision ignores that barrel for the same tick.

## Bank 3 beam traps (`raw 0x3B/0x3E`, bank 3 tiles around `26..36`)

The earlier implementation animated the whole three-cell beam in/out.  That was too literal from the draw refs.  The visual behavior is closer to a static device/end cap with only the middle discharge blinking.

Runtime behavior now keeps the end pieces static and flickers only the middle electric cel:

- vertical: end caps `27` and `26`, middle `28` idle, middle discharge `29/30` active;
- horizontal: end caps `32` and `33`, middle `34` idle, middle discharge `35/36` active.

## Shark swimmer (`raw 0x5F`, bank 4 tiles `44..47`)

The map code `0x5F` resolves to bank 4 tile `46` in the static TILE_MAP, but it is an enemy family in the animation/actor paths.  It is now extracted as a runtime swimmer instead of staying baked into the background.

Runtime behavior added:

- four-frame loop bank 4 `44..47`;
- actor-style `DS:34D6` frame counter;
- `2 px/tick` horizontal swim movement;
- reverses on body collision / level edge;
- does not require a floor probe, unlike walking enemies.

This is intentionally separated from regular walkers because water/swimmer enemies should not test for ground support.
