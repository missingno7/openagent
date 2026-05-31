# Pass 103 — low-latency render interpolation cleanup

## Context

Playtesting with `--interpolate-render` showed small stutters even though the
simulation still advanced on fixed DOS ticks.  This pass keeps all gameplay on
the existing fixed-tick path and changes only render-only interpolation state.

## Problems found

1. Player interpolation used a per-Tk-frame guard when capturing the previous
   render position.  If one UI frame caught up by running more than one DOS tick,
   the next draw could interpolate from the state at the start of the UI frame
   to the final catch-up state, spanning multiple DOS ticks and causing a hitch.
2. Dynamic entity snapshots intentionally captured pre-tick actor positions, but
   they also forced a player snapshot even when the actor tick did not move the
   player.  That could collapse an in-progress player lerp to the current pose.
3. Interpolated positions were floored with `int()`, biasing every fractional
   render coordinate backwards and producing an uneven pixel cadence.
4. Level-0/world-map player and camera render positions were still effectively
   un-interpolated, so the top-down map could feel jerkier than missions.
5. The main Tk callback clamped `dt` to `1/20` seconds, but one original DOS
   tick is about 54.9 ms.  Under high zoom or a late Tk callback this cap was
   smaller than one simulation tick, so the accumulator could visibly stutter
   or slow down instead of catching up.

## Implementation

- `openagent/runtime.py`
  - removed the per-Tk-frame guard from `snapshot_player_render_position()`
  - entity ticks now record the player's pre-actor pose only when the actor tick
    actually mutates the player, such as moving-platform carry
  - `render_interpolation_alpha()` gets a small clamped presentation lookahead
    based on the last UI-frame delta; this reduces apparent latency without
    simulating input/collision ahead
  - dynamic render coordinates now use nearest-pixel snapping instead of floor
  - level-0 player render interpolation is enabled
  - level-0 camera registers `DS:6838/683A` get a render-only previous/current
    pair, preserving fixed-tick gameplay camera semantics while smoothing the
    displayed scroll
  - the outer `tick()` loop now clamps only extreme stalls, not every frame to
    less than one DOS tick
  - the next Tk callback is scheduled after subtracting time already spent in
    update/draw, keeping cheap frames near 60 Hz and letting expensive frames
    drop naturally instead of queuing stale callbacks
- `openagent/overworld.py`
  - captures the previous world camera registers before each fixed world tick
- `tools/check_render_interpolation.py`
  - adds GUI-free regression checks for catch-up snapshotting, lookahead alpha,
    player interpolation, world-camera interpolation, and the no-`1/20` clamp
    timing rule

## Notes

The final framebuffer is still composed at the DOS source resolution and then
nearest-neighbor scaled.  That preserves the pixel-art look and keeps the patch
safe, but it also means interpolation is still quantized to source pixels before
zoom.  A future, more invasive renderer could composite dynamic sprites after
scaling to allow sub-source-pixel movement at high zoom.
