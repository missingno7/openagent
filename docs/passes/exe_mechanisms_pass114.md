# Pass 114 — unified render presentation smoothing

Goal: make the optional interpolation/smoothing path simpler and more useful for camera-relative jitter, especially when the player rides moving platforms.

## Problem

Pass 104 fixed the most obvious carried-player/platform phase bug by using the same fixed-step alpha for actors and player. Pass 110 then added a three-sample curve, but in constant-velocity cases it collapsed almost exactly to linear interpolation, so it was hard to see a difference. Camera quantization could still make platform riding look slightly jittery because player, platform and camera presentation were effectively handled by separate bits of code.

## Runtime changes

- Added `openagent/interpolation.py` with tiny generic render-only helpers:
  - `lerp_point()` for the normal fixed-tick target.
  - `PresentationSmoother` for framerate-independent display-position following.
- Simplified `openagent/rendering.py` so every renderable starts from the same linear target:
  - player
  - actor/entity slots
  - world-map camera
  - mission camera
- Smooth mode now applies the same presentation filter to those targets instead of a special older/previous/current Hermite path.
- Large jumps snap immediately to avoid smearing teleports, level loads, spawns and resets.
- Removed unused older-sample interpolation state from runtime/rendering/tests.

## Accuracy boundary

This pass intentionally changes only presentation. Fixed-tick simulation, collision, actor ordering, platform carry, projectiles, death behavior and interaction checks still read integer gameplay state, not smoothed render positions.

## Validation

```bash
python tools/check_handoff.py
python run_openagent.py --help
timeout 5s xvfb-run -a python3 run_openagent.py --level 1 --zoom 1 --smooth-render
```

The `xvfb-run` launch was expected to be stopped by timeout; it reached the Tk loop without a traceback.
