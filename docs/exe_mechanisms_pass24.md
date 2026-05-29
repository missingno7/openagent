# Pass 24 — satellite timing, platform speed, multi-tile actors, projectile sprites

## Satellite 0x23 / bank 10 tiles 0..3

The previous pass over-corrected this actor.  The special actor entry for raw
`0x23` creates object `0x0097`, behaviour state `0x20`, and timer period
`DS:34D8 = 3`.  In practice this is the visible satellite phase cadence:

```text
bank10: 0 -> 1 -> 2 -> 3, every 3 DOS ticks
```

Runtime `Satellite` now stores an explicit `frame_index` and `timer_ticks` and
is advanced only from the fixed DOS actor tick.  The accidental increments from
`draw_entities()` / `platform_below()` have been removed, which was another
source of unstable animation speed.

## Moving platform 0x62

The platform still starts left, but now moves as a 2 px/DOS-tick actor-style
mover.  The old 1 px/tick value was visibly too slow.  The exact raw-token init
branch for `0x62` still needs to be isolated, but this is now closer to the
integer-step actor movement paths than the previous fallback.

## New runtime actors from the already extracted special actor table

The following raw codes are now promoted from static map sprites to runtime
actors, so their original marker is skipped from the static background:

| raw | object id | state | speed | visible layout |
| --- | --- | --- | --- | --- |
| `0xAE` | `0x0353` | `0x2A` | 2 | bank 0, two-wide creature pairs `(0,4)..(3,7)` |
| `0x24` | `0x0065` | `0x27` | 2 | bank 2, two-high helmet actor, top `40..43`, bottom `44..47` |
| `0x56` | `0x0321` | `0x1E` | 2 | bank 12, two-high actor |
| `0x58` | `0x0331` | `0x1F` | 2 | bank 12, two-high actor |
| `0x63` | `0x0345` | `0x21` | 2 | bank 12, one-tile actor |

The bank-2 helmet actor is only a first mechanical pass: the EXE state clearly
has a separate behaviour branch, and the next target is to separate body walking
from helmet-open vulnerable frames.

## Projectiles

Player and bank-14 guard shots are now drawn using decoded bank-10 projectile
sprites instead of debug rectangles.  Both use bank 10 tiles `10/11`, matching
the visible projectile family already present in the game data.
