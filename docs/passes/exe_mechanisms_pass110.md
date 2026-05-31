# Pass 110 — optional three-sample render smoothing mode

## Goal

Playtesting showed that the pass-104 linear interpolation path was still a bit
jittery in situations where the fixed-tick gameplay itself advances in uneven
integer-sized steps, especially while riding moving platforms.  This pass adds a
second, more aggressive presentation mode without changing gameplay, collision,
ASM tick order, or fixed-tick state.

## Implementation

- Kept the existing linear render interpolation as the baseline.
- Added an optional smooth mode controlled by:
  - CLI: `--smooth-render`
  - runtime key: `I` cycles `off -> linear -> smooth -> off`
- Kept one extra presentation-only sample for each interpolated stream:
  - player: `older -> previous -> current`
  - dynamic actors/projectiles/score popups: `older -> previous -> current`
  - level-0 world camera registers: `older -> previous -> current`
- Added a monotone Hermite-style three-sample curve in `openagent/rendering.py`.
  It estimates incoming velocity from the older sample, but clamps the result to
  the previous/current fixed-tick interval so teleports, stops, and direction
  reversals cannot overshoot gameplay.
- The smooth curve collapses to exactly linear interpolation for constant-speed
  movement, so carried player/platform pairs remain phase-aligned when their
  fixed-tick history is the same.

## Non-goals

- No simulation smoothing.
- No collision smoothing.
- No extrapolation past the current fixed DOS-tick state.
- No future-frame buffering that would add a full tick of input latency.

## Files changed

- `openagent/rendering.py`
- `openagent/runtime.py`
- `openagent/window.py`
- `openagent/overworld.py`
- `tools/check_render_interpolation.py`
- docs/README/performance/pass indexes

## Verification

```bash
python -m compileall -q openagent tools
python tools/check_render_interpolation.py
python tools/check_handoff.py
python run_openagent.py --help
```


## Superseded note

Pass 114 keeps the same user-facing `smooth` mode but replaces this first three-sample/Hermite implementation with a simpler shared presentation follow filter in `openagent/interpolation.py`. Prefer pass 114 for current interpolation behavior.
