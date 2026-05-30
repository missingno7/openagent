# EXE mechanisms pass 11: player jump grounding and shooting states

This pass fixes two regressions found while comparing the prototype with the
unpacked `SAM1_unlz.exe` disassembly.

## Jump start / grounded probe

The previous runtime landed the player at `bottom == tile_top - 1`, but then
`refresh_grounded_state()` checked only a tiny epsilon around the current bottom
pixel. That made an exactly standing player look airborne, so Space could fail to
start a jump.

The grounded refresh now probes one DOS pixel below the player's collision box,
matching the EXE-style foot probe concept: if the two x probes at `x+3` and
`x+12` see `+0x1CC` or downward-valid `+0x1CD` under the player, the player is
standing. If those probes lose support, falling starts immediately.

## Shooting states

The fire-key branch in the disassembly is the code around `0x16F..0x302` in the
linear listing. It checks the configured fire key at `70C2`, skips shot creation
while `69F5` jump is active, and then chooses the shot direction by testing the
current player state:

- states `0x01`, `0x09`, `0x0B`, `0x0D` are treated as right-facing;
- otherwise the shot is left-facing.

The actual arm-extended shooting animation states set by this branch are:

- `DS:3500 = 0x0B` for shooting right;
- `DS:3500 = 0x0C` for shooting left.

The decoded player bank is zero-based, while the usual hand labels are one-based:

- bank 13 frame 10 = zero-based tile 9 = shoot right;
- bank 13 frame 11 = zero-based tile 10 = shoot left;
- bank 13 frame 13/14 = zero-based tile 12/13 = jump/air right/left;
- bank 13 frame 15/16 = zero-based tile 14/15 = death, never used for normal
  shooting or jumping.

The prototype now maps `0x0B/0x0C` to shooting tiles 9/10 and keeps `0x0F/0x10`
on jump tiles 12/13.

## Runtime behavior change

The prototype now treats Ctrl like the EXE key flag: the shooting frame is held
only while Ctrl is physically held, and one projectile is spawned on the press
edge subject to ammo/cooldown. This avoids the previous "sticky" shooting frame
that was caused by an arbitrary timer.
