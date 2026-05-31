# EXE mechanisms pass 108 — render-path cleanup split

Cleanup-only pass. No intended gameplay or ASM behavior changes.

## What changed

- Added `openagent/rendering.py` with `RenderingMixin`.
- Moved render-only helpers out of `openagent/runtime.py`:
  - render interpolation snapshots and alpha calculation,
  - camera projection, including death-camera/world-camera presentation,
  - `draw()` and small Tk/PIL frame composition helpers,
  - player/entity/beam/code sprite drawing helpers.
- Trimmed imports from `runtime.py` that were only used by the moved draw path.
- Updated README, project map, performance notes, next-research queue, pass index, and mechanisms summary.

## Guardrails

`openagent/rendering.py` is presentation-only. It may read fixed-tick state and render snapshots, but it should not mutate gameplay, collision, pickups, damage, score, or progression.

`openagent/runtime.py::update_mission_simulation()` remains the owner of fixed-step ordering. Do not reintroduce separate player/entity accumulator loops while continuing cleanup.

## Verification

```text
python tools/check_handoff.py
python run_openagent.py --help
```
