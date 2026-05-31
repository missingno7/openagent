# Pass 102 — overworld marker cleanup, completed-house re-entry gate, full death reset

## Context

This pass fixes three regressions found during playtesting after the pass-101
overworld entry/animation work:

1. Raw level-0 player marker `0x59` remained baked into the cached world image,
   so the live player could be drawn twice after moving away from the start.
2. Completed/checkmarked houses should remain valid entrances after the player
   leaves and walks back into them.
3. Hard-death level restart should restore the mission health/lives state rather
   than re-applying the already-decremented life counter after `load_level()`.

## Evidence / reasoning

- The level-0 `0x59` raw code is a player start marker. Pass 101 aligned the
  live world-map player to `DS:34EE/34F0`; keeping the raw marker in the static
  renderer made the marker visible as a second player sprite.
- Passes 98–101 keep collision/movement on ASM-backed data, but the house entry
  release gate was a port-side safety guard. It used broad 10x16 body overlap
  and could stay armed while only the edge of the body still touched the just
  completed house. Entry/release is now based on the player origin entering the
  house footprint, so checked houses can be replayed after leaving and walking
  back in.
- `respawn_after_death()` already called `load_level(reset_player=True)`, but
  then restored the decremented `lives` value. That contradicted the intended
  full mission restart behavior for hazards such as water/laser death.

## Implementation

- `openagent/runtime.py`
  - imports `WORLD_PLAYER_CODE`
  - skips raw `0x59` while rendering level 0, so only the live player draw path
    paints the world-map player
- `openagent/overworld.py`
  - adds `world_player_origin_inside_cells()`
  - changes the post-return release gate and entrance dispatch to use the
    player origin inside the house footprint instead of broad body overlap
  - completed houses remain active because completion state only changes the
    visual checked overlay, not the source entrance mapping
- `openagent/player_lifecycle.py`
  - removes the post-reset restoration of decremented `lives` and `score`
  - lets `load_level(reset_player=True)` define the complete mission reset
    state, including `DS:6A40`/HUD health
- `tools/check_overworld_collision.py`
  - adds a completed-house re-entry regression check
- `tools/check_death_reset.py`
  - adds a focused death-reset smoke test

## Remaining gaps

- Exact entrance-to-level mapping is still row-major prototype behavior.
- Persistent completion/progression storage is still runtime-local.
- The exact far restart helper after `DS:69F6 == 0` still needs a deeper trace if
  we want to prove score/ammo/inventory persistence beyond the current full
  reset policy.
