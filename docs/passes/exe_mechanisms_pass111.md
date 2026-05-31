# Pass 111 — Cleanup: movement/collision extraction

Scope: cleanup/refactor only. No intended gameplay or ASM behavior change.

## What changed

- Added `openagent/movement_collision.py` with `MovementCollisionMixin`.
- Moved low-level mission player movement, runtime collision-grid queries, moving-platform/barrel landing helpers, and actor-solid probes out of `runtime.py`.
- `runtime.py` now remains the owner of application setup, level load/reset, fixed-step timing, actor update ordering, and interaction dispatch.
- Trimmed runtime imports that were only needed by the extracted movement/collision helpers.

## Why

The remaining `runtime.py` file was still mixing several responsibilities after the render/window/teleporter extractions.  Movement/collision is a coherent subsystem with lots of ASM-sensitive details, so isolating it reduces the risk of accidentally changing fixed-step orchestration while editing collision mechanics.

## Current ownership rule

- `runtime.py` owns when a mission tick runs and in what order systems execute.
- `movement_collision.py` owns how player/barrel/platform movement probes and runtime collision checks are performed.
- `rendering.py` owns presentation-only interpolation and draw state.
- `combat.py`, `teleport.py`, `overworld.py`, `window.py`, and `hud.py` remain focused mixins.

## Validation

```text
python tools/check_handoff.py
python run_openagent.py --help
```

Both passed after the extraction.
