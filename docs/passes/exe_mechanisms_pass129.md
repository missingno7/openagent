# EXE mechanisms pass 129: stationary projectile pass-through and raw 0x3C/0x3D rockets

Focus: re-audit projectile behavior for the stationary launcher family after the user observed that shots from raw `0x51`/`0x52` and rockets from raw `0x3C`/`0x3D` should pass through the player instead of being consumed.

## ASM findings

### Launcher states and spawn parameters

`SAM1:0x6B74..0x6D47` handles the stationary launcher family.

- Raw `0x52` / state `0x0A` fires object `0x01D6` from `actor_x + 8, actor_y`, direction `+1`, speed `4`.
- Raw `0x51` / state `0x0B` fires object `0x01D6` from `actor_x - 8, actor_y`, direction `-1`, speed `4`.
- Raw `0x3C` / state `0x0C` fires object `0x01E8` from `actor_x + 16, actor_y`, direction `+1`, speed `4`.
- Raw `0x3D` / state `0x0D` fires object `0x01EC` from `actor_x - 16, actor_y`, direction `-1`, speed `4`.

The cadence logic is the same elapsed-timer row/front gate already traced in pass 119: `DS:34DA` increments before the row/front tests and resets only after a successful helper `0x5784` spawn.

### Projectile active states

Helper `0x5784` maps:

- object `0x01D6` to projectile state `0x07`,
- objects `0x01E8` and `0x01EC` through the default projectile path, state `0x0E`.

Both projectile update states route player overlap through helper `0x53C4`. That helper hurts the player when the 10x16 projectile rectangle overlaps the player's origin gameplay rectangle, but it does not rewrite or remove the projectile slot. Projectile consumption is owned by the separate `0x547C` impact branch.

Therefore player contact should hurt the player but the shot/rocket should continue moving through the player.

## Python changes

- Stationary launcher projectiles now use `keep_on_player_hit=True`.
- The same pass-through player-hit rule is used for raw `0x51`/`0x52` shot object `0x01D6` and raw `0x3C`/`0x3D` rocket objects `0x01E8`/`0x01EC`.
- The `0x53C4` 10x16 hit rectangle is represented with `narrow_hurt_on_hit=True`, `hit_w=10`, `hit_h=16`.
- The existing visual anchor compensation is now explicit: Python stores horizontal projectile `y` as `actor_y + 7` for rendering, while `hit_y_offset=-7` keeps the damage rectangle at the ASM helper `actor_y`.
- Raw `0x3C` is represented as a right-facing stationary launcher; raw `0x3D` is left-facing. The `0x3D` spawn now verifies the ASM `actor_x - 16` origin.

## Regression checks

`tools/check_stationary_shooter_accuracy.py` now checks:

- raw `0x51`/`0x52` projectile `0x01D6` hurts but remains active after crossing the player,
- raw `0x3C` rocket spawn uses `actor_x + 16`, `actor_y`, direction `+1`, speed `4`, and passes through the player,
- raw `0x3D` rocket spawn uses `actor_x - 16`, `actor_y`, direction `-1`, speed `4`, and passes through the player,
- raw `0x51`/`0x52` bodies still remain non-solid and non-contact-harmful.

## Remaining gaps

- `0x547C` impact side effects are still only modeled broadly as solid/tile impact and optional visible impact state.
- The complete projectile object/state table beyond this stationary launcher family remains incomplete.
- DOSBox pixel captures would still be useful to confirm sprite-top alignment at row boundaries.
