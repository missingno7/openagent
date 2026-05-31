# EXE mechanisms pass 100 — level-0 overworld movement/camera audit

User testing after pass 99 showed that the world-map collision table was closer,
but navigation still did not feel like the DOS game and some map areas could be
hard to reach.  This pass therefore re-read the movement routine itself instead
of only the collision-byte builder.

## ASM evidence

- `SAM1:0xBAF5..0xBC0A` is the level-0 top-down movement branch selected when
  `DS:681C == 1`.
- `SAM1:0xB7D9..0xB8B0` is the destination collision helper used by that branch.
- `SAM1:0x2059..0x209F` recenters/clamps the world scroll registers after a
  teleport-style reposition.

The movement routine saves the previous player origin, then processes direction
flags in a fixed order: right, left, down, up.  Horizontal movement calls the
same `0x532D` acceleration/ramp helper as mission movement.  Vertical world-map
movement is fixed at 4 px per DOS tick.

The collision helper receives the attempted displacement, adds it to
`DS:34EE/34F0`, and samples the runtime body byte `+0x1CC` at the four corners
of the 10x16 gameplay body: `x+3`, `x+12`, `y`, `y+15`.  The caller only writes
`DS:34EE/34F0` after the helper reports clear.

## Runtime changes

- World movement now calls dedicated `move_world_right/left/down/up` helpers
  instead of the generic axis wrapper.
- The attempted offset is checked before writing the player position; runtime no
  longer pre-clamps destinations to the 16x20 decoded sprite bounds.
- The fixed ASM flag order is preserved: right, left, down, up.
- Level-0 camera is no longer the generic center-on-player camera.  Runtime now
  models the scroll registers:
  - `DS:6838` X scroll, clamped `0..0x140`.
  - `DS:683A` Y scroll, clamped `0..0xB8`.
  - right scroll threshold `camera_x + 0xAA < player_x`.
  - left scroll threshold `camera_x + 0x96 > player_x`.
  - vertical scroll threshold `camera_y + 0x50`.
- Entering/resetting the overworld and arriving from world-map teleporters now
  initialize the camera like `SAM1:0x2059`: `player_x - 0xA0`, `player_y - 0x64`,
  then clamp.

## Not changed in this pass

The pass-99 `CS:0x2E20` world collision parser is retained.  In particular,
raw `0x55` and `0x61` remain body-solid on the overworld, while raw `0x30`
remains body-clear according to the recovered table.  The user's reported
"solid-looking gap" can still be consistent with the EXE because the world-map
player body is only 10 px wide and collision checks bytes, not the full 16 px
sprite art.

## Remaining gaps

- Exact entrance marker dispatch and completion flags.
- Original popup/table windows on the overworld.
- Coordinate-by-coordinate comparison with a DOS capture for any remaining
  suspicious map choke points.
