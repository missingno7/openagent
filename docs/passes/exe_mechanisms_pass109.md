# EXE mechanisms pass 109 — runtime cleanup split

Cleanup-only pass. No intended gameplay or ASM behavior changes.

## What changed

- Moved static level-image cache/render helpers from `openagent/runtime.py` into `openagent/rendering.py`:
  - `current_tile_anim_tick()`,
  - `render_level_image_for_phase()`,
  - `draw_open_exit_door_overlays()`.
- Added `openagent/window.py` with `WindowMixin` for Tk/input/navigation helpers:
  - keyboard event handling,
  - zoom/window sizing,
  - episode/level switching,
  - window title updates.
- Added `openagent/teleport.py` with `TeleportMixin` for the reconstructed teleporter state machine and release gate.
- Promoted raw water/hard-death visual constants into `openagent/semantics.py` so runtime no longer owns local map-code facts.
- Trimmed unused imports from `runtime.py` after the extractions.

## Current ownership after this pass

- `runtime.py` owns application construction, level reset, frame pacing, mission fixed-step order, collision/movement glue, actor tick dispatch, and interaction dispatch.
- `rendering.py` owns render-only presentation, static/dynamic compositing, interpolation snapshots, camera projection, and level-image cache refresh.
- `window.py` owns Tk window controls and keyboard shortcuts.
- `teleport.py` owns mission/world teleporter touch, countdown, target selection, and release gating.

## Guardrails

Keep the single fixed-step owner in `runtime.py::update_mission_simulation()`. Splitting helpers is fine; reintroducing separate player/entity accumulator loops is not.

`rendering.py` should still have no gameplay side effects. `teleport.py` may mutate teleporter/player warp state, but should not become a general interaction dispatcher.

## Verification

```text
python tools/check_handoff.py
python run_openagent.py --help
```
