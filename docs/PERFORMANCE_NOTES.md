# Performance Notes

Current runtime performance priorities are rendering cost, map-cell lookup cost, and avoiding avoidable Tk/PIL allocations at high zoom.

## Current decisions

- The simulation still advances on fixed Secret Agent/DOS-style ticks. Tk may call the outer loop more often, but without render interpolation the runtime skips frames whose visual state key has not changed.
- The Tk canvas owns one persistent image item. Per-frame drawing updates/reuses the `PhotoImage` when the scaled framebuffer size is unchanged.
- Zoom is output-only. Gameplay and collision stay in unscaled 16px tile coordinates.
- `LevelInfo` map-cell/layout data is cached by `openagent.level_model`. Hot calls like `cells_at()` and `visual_coverage_cells()` should use these helpers instead of rescanning raw map rows.
- Runtime collision grids are cached in `OpenAgentApp.runtime_collision_grid()` using level/state/removal keys. Do not rebuild them directly in tight loops unless the inputs changed.

## Hot paths to keep clean

- `openagent/runtime.py::tick()` should decide whether drawing is necessary before calling `draw()`.
- `openagent/runtime.py::draw()` should remain allocation-aware: crop/paste the cached level image, draw dynamic overlays, then resize once for zoom.
- `openagent/runtime.py::alpha_composite_clipped()` avoids crop allocation for fully visible tiles; use it for small live overlays that may be partly outside the camera.
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
