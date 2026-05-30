# Pass 74 – cleanup-only combat/projectile extraction

This pass is a structural cleanup. It intentionally does not change gameplay logic.

## What moved

Moved the large projectile/combat block out of `openagent/runtime.py` into:

- `openagent/combat.py`

`OpenAgentApp` now inherits `CombatMixin` alongside the existing HUD and player lifecycle mixins.

## Why

The projectile/damage section had become one of the largest self-contained blocks in `runtime.py` and is also one of the highest-change areas for future ASM-backed work:

- player bullet creation and cooldown policy,
- enemy projectile spawning,
- laser/lightning/shrapnel projectile variants,
- projectile impact state,
- enemy hit policy,
- actor hit rectangles,
- score popup helper,
- special hit cases such as raw `0x24` helmet vulnerability and bank-14 guards.

Keeping this together in `combat.py` should make future projectile/hit research safer and easier to review.

## Invariants

No intentional gameplay changes:

- copied methods verbatim from the pre-pass74 runtime block,
- kept method names and call sites stable,
- left entity data shapes in `entities.py`,
- left player damage/death lifecycle in `player_lifecycle.py`.

## Validation

- `python tools/audit_project.py`
- import check for `openagent.runtime` and `openagent.combat`
