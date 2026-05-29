# Pass 29: projectile impact sprites and shootable/indestructible actor properties

This pass corrects two earlier over-generalisations in the runtime port.

## Bullet impact animation

The runtime previously drew projectile impact with bank 6 tiles. That was the
wrong visible family. The in-game bullet hit spark is the four-frame sequence in
bank 5:

- bank 5 tile 24
- bank 5 tile 25
- bank 5 tile 26
- bank 5 tile 27

The EXE still rewrites the actor slot into the same impact-state family in the
projectile/actor collision path, but the decoded atlas lookup points at the bank
5 frames for the visible spark. Runtime `Explosion` now renders bank 5 `24..27`.

## Not every actor slot is damageable

Earlier passes treated everything stored in `entities.enemies` as something a
player projectile can damage. That is not how the original code is structured.
The hit dispatcher around `SAM1:0x4BD2..0x4ED5` branches mainly on the actor
object id in `DS:34E0`, not on “is this in the actor list”.

Currently decoded damage branches:

- `0x0353`: special wide hit-test for the two-tile bank 0 dog.
- `0x0321..0x0383`: large/multi-hit enemy family.
- `0x1389`: related special hit branch.
- `0x0072`: object-specific branch.
- `0x0065`: object-specific branch used by the bank 2 two-tile helmet actor.
- bank 14 guards use their own degrade chain, already modelled separately.

The stationary shooter / rocket launcher actors are not in these shot-damage
branches:

- raw `0x52`, object `0x01D0`, state `0x0A`
- raw `0x51`, object `0x01D1`, state `0x0B`
- raw `0x3C`, object `0x01E7`, state `0x0C`
- raw `0x3D`, object `0x01EB`, state `0x0D`

So the runtime now treats them as solid indestructible map actors: they can fire
when their viewport/line-of-sight timer allows it, and bullets impact/explode on
them, but shooting them does not remove or damage them.

## Runtime changes

- Added `object_id_is_shootable()` and object-id damage classification in
  `openagent/exe_actor_mechanics.py`.
- `hit_enemy_with_projectile()` is now only entered for actors that match the
  decoded shootable object-id branches or the bank-14 guard chain.
- Stationary shooters block the player/projectiles as solid actor objects but
  are not damageable.
- Bullet impact renders bank 5 tiles `24..27`.

See `docs/derived_mechanics/pass29_hit_properties.json` for the current decoded
actor list with hit classifications.
