# EXE Mechanisms Pass 40 - Raw 0x6E Lightning Flyer

## Summary

Raw mission code `0x6E` is not a simple walking enemy.  The spawn table creates:

- object id `0x0085`
- state `0x26`
- horizontal speed `2 px/tick`
- random initial direction
- `DS:34D8 = random(0x14) + 0x1E`
- `DS:34DE = random(0x32) + 0x64`
- `DS:34DC = 3`

The state `0x26` branch at `SAM1:0xA70F..0xA894`:

- reverses horizontal direction on collision/edge;
- advances the normal `DS:34D6` frame counter;
- if `34DE > 0`, decrements it and restores the old X position, making the
  actor pause in place;
- when `34DE == 0`, increments `34DA`;
- when `34DA == 0`, spawns object `0x89` at `(actor_x, actor_y + 16)` via
  projectile helper `0x5784`;
- when `34DA == 34D8`, resets `34DA = 0` and sets `34DE = 0x6E`.

Object `0x89` is handled by the projectile helper as state `0x28` with
`DS:34DA = 0x1E`.  The state `0x28` branch animates in place until the timer
expires and then clears the actor slot.

## Runtime Mapping

The flyer itself uses bank 2 tiles `32..35`, mirrored when travelling left.
The spawned lightning uses bank 2 tiles `36..39` as a separate stationary
hostile actor below the flyer for 30 ticks.  Unlike horizontal bullets, it is
drawn at its actor origin as a full 16x16 hazard tile.

This corrects the earlier interpretation that bank 2 tiles `36..39` were just a
left-facing animation range for the flyer.
