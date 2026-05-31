# Pass 104 — linear render interpolation/platform phase fix

Playtesting after pass 103 showed that `--interpolate-render` could look worse
while riding moving platforms.  The visible symptom was not a physics bug: the
platform advanced on the fixed actor tick and carried the player, but the
player's previous render pose was captured later by the player-control tick.
That made the platform render as `old -> new` while the carried player often
rendered as `new -> new` for the same DOS tick.

## Changes

- Mission updates now use `OpenAgentApp.update_mission_simulation()` as one
  fixed-step loop for dynamic actor slots and player control.
- Before every mission DOS tick the renderer snapshots both:
  - all dynamic actor positions, and
  - the player position.
- The fixed tick then advances actors first, then player/death/interactions,
  preserving the previous runtime order but giving interpolation one coherent
  `previous -> current` interval.
- `entity_render_position()` and `player_render_position()` now use the same
  `_logic_accum` presentation fraction.
- Removed the pass-103 presentation look-ahead.  `render_interpolation_alpha()`
  is now the plain linear `accumulator / DOS_tick` clamp.
- `tools/check_render_interpolation.py` now includes a moving-platform carried
  player regression check.

## Intentional non-changes

- Gameplay, collision and ASM fixed-tick mechanics are still not interpolated.
- Rendering is still snapped to source pixels before nearest-neighbor zoom, so
  very slow 1 px/tick movement is still limited by pixel cadence.  The important
  fix is that related objects now share the same pixel cadence instead of being
  one render phase apart.
