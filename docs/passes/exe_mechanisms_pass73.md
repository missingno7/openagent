# Pass 73 - cleanup: shared constants and player lifecycle split

This pass is intentionally a maintenance-only refactor.  No gameplay rules were
changed.

## Why

`openagent/runtime.py` had started to accumulate unrelated responsibilities:
window sizing, DOS-tick constants, player physics constants, HUD constants,
hurt/death lifecycle, projectiles, entity logic, rendering, and map interaction.
That made it easy to mix up researched ASM facts with temporary port behaviour.

## Changes

- Added `openagent/game_constants.py` for shared runtime constants:
  - 320x200 playfield dimensions
  - 320x192 active gameplay viewport and 8px HUD strip
  - zoom limits
  - DOS tick rate
  - player collision dimensions
  - jump/fall tables
  - starting/max ammo constants
- Added `openagent/player_lifecycle.py` with `PlayerLifecycleMixin`:
  - `hurt_player()`
  - `kill_player()`
  - `spawn_player()`
  - `respawn_after_death()`
- Updated `OpenAgentApp` to inherit `HUDMixin, PlayerLifecycleMixin`.
- Removed the copied constant block and lifecycle methods from `runtime.py`.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/audit_project.py
PYTHONDONTWRITEBYTECODE=1 python -c "import openagent.runtime, openagent.game_constants, openagent.player_lifecycle; print('imports ok')"
```

## Next cleanup candidates

- Extract projectile spawn/update/hit policy into a `ProjectileMixin`.
- Extract static-map interactions/pickups into a separate interaction module.
- Extract enemy state update dispatch into per-state helpers.
