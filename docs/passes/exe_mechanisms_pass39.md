# EXE Mechanisms Pass 39 - Projectile Viewport Cull

## Summary

Projectile slots are bounded by the active DOS gameplay viewport, not by the
whole level.  The actor/projectile movement code around `SAM1:0x7FAD..0x8105`
compares actor position against the scroll/player viewport state and the scroll
variable `DS:6838`, which is clamped to `0..0x140` elsewhere.

Runtime implication:

- a moving projectile that fully leaves the fixed 320x200 active viewport is
  removed without creating an impact animation;
- impacts still happen when the projectile hits a solid runtime cell or a
  blocking/shootable actor before it leaves that viewport;
- the cull is independent of the resizable render window.

This matters for player firing because the player shot is slot-based.  Once the
bullet leaves the active viewport, the slot frees and another shot can be fired.
