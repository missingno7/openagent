# Pass 113 — raw 0x4D mine triggered explosion fan-out cleanup

This pass rechecked the visible triggered-mine explosion because playtesting
showed one central mine explosion plus three extra persistent explosion sprites.
That was a leftover approximation from older builds.

## ASM evidence

The relevant state is raw `0x4D` after it has been rewritten from idle object
`0x0270` into triggered object `0x0271/state 0x17`.

- `SAM1:0x7782..0x78C1` is the state-`0x17` update branch.
- `SAM1:0x7791` increments `DS:34D6`.
- `SAM1:0x779C..0x77BA` calls helper `0x53C4` when `DS:34D6 == 0x0B`.
- `SAM1:0x77C4..0x77DB` special-cases object `0x0271` once `DS:34D6 > 0x0B`.
- `SAM1:0x77E0..0x78A4` calls the original draw/clear helpers for the blast
  around the mine position.

Important implementation point: this branch draws/clears through the original
render helpers. It does **not** allocate additional persistent projectile-impact
actors. The port should therefore keep the triggered mine actor as the only
runtime explosion object.

## Runtime change

Removed the old approximation from `OpenAgentApp.update_entities_tick()`:

```python
self.spawn_projectile_explosion(enemy.x + TILE / 2, enemy.y + TILE / 2)
self.spawn_projectile_explosion(enemy.x - TILE / 2, enemy.y + TILE / 2)
self.spawn_projectile_explosion(enemy.x + TILE * 1.5, enemy.y + TILE / 2)
```

The triggered mine now only advances its own state-`0x17` visual through
`state17_landmine_tile()`. The secondary frame-`0x0B` `0x53C4` contact check is
kept, because it is explicitly present in ASM.

Also removed the unused `STATE17_LANDMINE_TRIGGER_TILES` constant, which belonged
to an older bank-5 `42..44` approximation and is no longer a source of truth.

## Regression

Added:

```bash
python tools/check_landmine_no_extra_explosions.py
```

The test constructs a triggered object `0x0271/state 0x17` at the frame that used
to spawn the fan-out and asserts that no `Explosion` entities are allocated.
