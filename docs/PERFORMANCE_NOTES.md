# Performance Notes

Current runtime performance priorities are rendering cost, map-cell lookup cost, and avoiding avoidable Tk/PIL allocations at high zoom.

## Current decisions

- The simulation still advances on fixed Secret Agent/DOS-style ticks. Tk may call the outer loop more often, but without render interpolation the runtime skips frames whose visual state key has not changed.
- Render interpolation is render-only: gameplay/collision stay fixed-tick, while previous/current poses are lerped for drawing. The main loop must never clamp `dt` below one DOS tick; late frames need to be allowed to catch up.
- Missions use one shared fixed-step simulation loop. Player, dynamic actors, moving platforms, and the death arc are snapshotted before the same DOS tick and drawn with plain linear `accumulator / DOS_tick` alpha by default.
- Optional `--smooth-render` / `I` smooth mode is now a shared presentation-only follow filter in `openagent/interpolation.py`. It starts from the same linear fixed-tick target as normal interpolation, then smooths the displayed player/entity/camera poses. Keep it render-only; do not feed smoothed values back into collision, actor logic, camera registers, or interaction tests. Large jumps should snap instead of smearing.
- Interpolated dynamic sprites are snapped to the nearest source pixel instead of floored; this avoids a biased pixel cadence while preserving the nearest-neighbor pixel-art renderer.
- The Tk canvas owns one persistent image item. Per-frame drawing updates/reuses the `PhotoImage` when the scaled framebuffer size is unchanged.
- Zoom is output-only. Gameplay and collision stay in unscaled 16px tile coordinates.
- `LevelInfo` map-cell/layout data is cached by `openagent.level_model`. Hot calls like `cells_at()` and `visual_coverage_cells()` should use these helpers instead of rescanning raw map rows.
- Runtime collision grids are cached in `OpenAgentApp.runtime_collision_grid()` using level/state/removal keys. Do not rebuild them directly in tight loops unless the inputs changed.

## Hot paths to keep clean

- `openagent/runtime.py::tick()` should decide whether drawing is necessary before calling `draw()`. It also owns frame pacing; keep the catch-up clamp above one DOS tick and run `tools/check_render_interpolation.py` after timing changes.
- `openagent/runtime.py::update_mission_simulation()` owns the mission fixed-step order. Do not reintroduce separate player/entity accumulator loops; platform carry and death animation depend on one shared snapshot phase.
- `openagent/rendering.py::draw()` should remain allocation-aware: crop/paste the cached level image, draw dynamic overlays, then resize once for zoom.
- `openagent/rendering.py::alpha_composite_clipped()` avoids crop allocation for fully visible tiles; use it for small live overlays that may be partly outside the camera.
- `openagent/rendering.py` is presentation-only. Do not add gameplay, collision, pickup, or damage side effects there. Static level-image cache refresh lives here only because it prepares the presentation layers. Linear and smooth interpolation modes must continue to share the same fixed-tick snapshots.
- `openagent/level_model.py` owns cached cell indexes. If a tool mutates `LevelInfo.raw`, call `invalidate_level_model_cache(info)`.

## Benchmark notes

The numbers below are approximate and were measured under `xvfb`, so use them as relative comparisons only.

### Map/cell helpers

| Operation | Before this cleanup | After this cleanup |
|---|---:|---:|
| `tuple(iter_map_cells(info))` | ~2.99 ms/call | ~0.016 ms/call |
| `cells_at(...)` | ~1.91 ms/call | ~0.0007 ms/call |
| `visual_coverage_cells(...)` | ~2.36 ms/call | ~0.0005 ms/call |
| `build_runtime_collision_grid(...)` | ~5.83 ms/call | ~3.60 ms/call |

### Forced full-frame draw

| Zoom | Before this cleanup | After this cleanup |
|---:|---:|---:|
| 1× | ~8.3 ms | ~6.8 ms |
| 2× | ~12.1 ms | ~10.0 ms |
| 3× | ~18.9 ms | ~18.2 ms |
| 4× | ~37.1 ms | ~33.9 ms |
| 6× | ~71.4 ms | ~68.7 ms |

High zoom is still naturally more expensive because the final image sent to Tk is larger. The important rule is to avoid redrawing unchanged frames and avoid recreating Tk canvas image objects.

## Handoff check

Use `python tools/check_handoff.py` before packaging. It runs the interpolation, overworld, death-reset, death-platform, mechanics-registry, and project-cleanliness checks without leaving bytecode caches in the tree.
