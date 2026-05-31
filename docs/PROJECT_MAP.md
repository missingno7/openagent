# Project Map

This cleanup pass makes the repository easier to navigate without changing gameplay logic.

## Runtime layer: `openagent/`

| File | Purpose | Notes |
|---|---|---|
| `runtime.py` | Application construction, level reset, frame pacing, mission fixed-step orchestration, actor tick dispatch, and interaction dispatch | Still the integration owner, but HUD, player lifecycle, combat/projectiles, movement/collision, overworld, render presentation, teleporter state, and Tk/window controls are now extracted. Missions advance through `update_mission_simulation()`; avoid reintroducing separate player/entity tick loops. |
| `rendering.py` | Render-only interpolation, presentation smoothing, camera projection, static level-image cache refresh, Tk/PIL frame composition, dynamic sprite draw helpers | Owns `draw()`, `render_level_image_for_phase()`, render snapshots, entity/player interpolation, camera smoothing, and sprite compositing. Keep gameplay/collision decisions out of this module. |
| `interpolation.py` | Shared presentation-only interpolation/smoothing helpers | Tiny generic lerp + exponential follow filter used by player, actors and camera; no game state or Tk dependency. |
| `window.py` | Tk window, keyboard shortcuts, zoom, episode/level navigation, title updates | UI/control-flow only; do not put simulation rules here. |
| `teleport.py` | Mission/world teleporter countdown, target selection, touch/release gates | Owns DS:69E0/69E2-style warp state. Keep unrelated pickup/interactions out. |
| `movement_collision.py` | Mission player movement probes, runtime collision-grid queries, platform/barrel landing/carry helpers | Extracted in pass 111. Keep low-level collision mechanics here, but keep fixed-step ordering in `runtime.py`. |
| `entities.py` | Runtime entity dataclasses and level extraction | Good place for actor/projectile data shapes, not behavior. |
| `combat.py` | Projectile spawning/update, combat hit policy, score popups, and actor hit helpers | Cleanup-only mixin extracted in pass 74. Future projectile/hit ASM findings should start here. |
| `overworld.py` | Level-0 island/world-map movement, camera, entrance trigger, completion redraw helpers | Keep exact entrance mapping/progression/popup guesses isolated here until ASM-backed. |
| `semantics.py` | Raw map-code categories and source-code meaning | Add raw-code classification here before touching runtime logic. |
| `animation.py` | Player/enemy tile-frame mapping | Put frame ranges here, especially when verified from ASM. |
| `player.py` | Player runtime dataclass/state fields | Keep state shape here; keep movement behavior in runtime or a future player system. |
| `hud.py` | Status bar + 8×8 UI text renderer | Owns `SAM?02.GFX` page constants, pass-93 fixed HUD slot map and fallback glyphs; no gameplay mutation. |
| `sound.py` | `.SND` loading/playback and sound IDs | Keep ASM sound IDs here; avoid ad-hoc numbers in runtime. |
| `level_model.py` | Runtime grid/cell helpers | Shared source of truth for cached map-cell iteration, `cells_at()`, visual coverage, and collision-grid input. |
| `exe_*` modules | Data extracted from ASM/disassembly | These should be small, factual, and cited in docs. |

## Game asset/data layer: `openagent/game_assets/`

| File | Purpose |
|---|---|
| `graphics.py` | ProGraphx 16x16 and 8x8 decoders shared by runtime and HUD. |
| `render.py` | Static level rendering from original map/tiles. |
| `bundle.py` | Episode asset loading. |
| `tile_animations.py` | EXE/data-derived tile animation and background variant helpers. |

## Reverse-engineering layer

| Path | Purpose |
|---|---|
| `dissassembly/` | Unpacked EXE and linear ASM references. Keep raw generated evidence here. |
| `dissassembly/annotated/` | Curated ASM excerpts with direct comments for tick-accuracy work. Start with `SAM1_tick_accuracy_excerpts.asm`. |
| `tools/` | Scripts that extract structured facts from ASM/assets. |
| `docs/passes/` | Chronological pass notes. Useful for audits, not for onboarding. |
| `docs/derived_mechanics/` | JSON/CSV extracted facts used for implementation. |

## Performance/cleanup status

- `openagent/level_model.py` now caches map-cell/layout indexes on `LevelInfo`; tools that mutate raw level data should call `invalidate_level_model_cache(info)`.
- `openagent/rendering.py` keeps one persistent Tk canvas image item and updates/reuses the `PhotoImage` where possible.
- Mission fixed-step simulation uses one shared accumulator/snapshot phase for player, actors, platforms, and death animation; old separate `update_player(dt)`/`update_entities(dt)` wrappers were removed in pass 107. Passes 108-109 moved render presentation, static level-image cache refresh, teleporter state, and Tk/window controls into focused mixins. Pass 110 added optional render smoothing, and pass 114 replaced that first three-sample curve with a shared presentation follow filter in `interpolation.py` so player, actors and camera use one simple algorithm. Pass 111 moved low-level movement/collision helpers into `movement_collision.py`; pass 112 restored the hard-death runtime visual lookup import and added a handoff smoke test for it; pass 113 added a triggered-mine no-extra-explosions regression; pass 118 added an ASM-backed raw-0xA7 player/barrel contact regression.
- `docs/PERFORMANCE_NOTES.md` records the current hot paths and local benchmark notes.

## Recommended next refactors

1. Continue splitting `openagent/runtime.py` by safe systems: next best targets are `interactions.py`, inventory/pickup handling, and smaller actor-state modules. Keep the single mission fixed-step loop in one owner while splitting behavior helpers out.
2. Replace remaining magic object IDs in runtime with names from `semantics.py`, `animation.py`, `sound.py`, or a new factual `object_ids.py`.
3. Keep UI/HUD work tied to `SAM?02.GFX` and ASM pointer pages (`DS:6E36`, `DS:6E3A`, `DS:6E32`). Do not reintroduce PIL-drawn fake glyphs except as explicit fallback for missing data.
4. Before handing off, run `python tools/check_handoff.py`; it avoids leaving `__pycache__` behind.
5. When adding mechanics, update `docs/MECHANICS_INDEX.md` and add a short pass note under `docs/passes/`.

### New cleanup modules from pass 73

- `openagent/game_constants.py` – shared dimensions, DOS tick rate, player physics tables, ammo constants. Keep pure constants here only.
- `openagent/player_lifecycle.py` – player damage/death/respawn lifecycle. Put ASM-backed hurt/death changes here instead of `runtime.py`.

## Accuracy tracking added in pass 76

Use these files before changing gameplay logic:

```text
docs/ACCURACY_STATUS.md              status labels and workflow
docs/ASM_EVIDENCE_INDEX.md           quick human-readable evidence map
docs/TICK_ACCURACY_LEDGER.md         ASM refs -> Python tick phases -> blind spots
docs/registry/mechanics_status.json  machine-readable mechanic registry
docs/registry/tick_accuracy_ledger.json machine-readable tick phase ledger
tools/audit_mechanics_status.py      registry validator
tools/audit_tick_accuracy.py         tick ledger validator
```

When a mechanic is changed, update its registry entry and, if it affects fixed-tick behavior, update `docs/registry/tick_accuracy_ledger.json` too. If behavior is discovered to be wrong during playtesting, downgrade the status instead of leaving it looking verified.
