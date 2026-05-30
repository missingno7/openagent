# EXE mechanisms pass 6: runtime animation implementation

This pass implements the animation behaviour that was identified in the previous
EXE analysis instead of leaving the runtime prototype on static sprites.

## Player animation

The unpacked EXE writes the player animation state at `DS:3500`.  The state ids
seen in the control/update code line up with the decoded player tile bank:

| EXE state | Runtime meaning | Implemented tile source |
| --- | --- | --- |
| `0x01` family | walk right | bank 13 tiles `0..3` |
| `0x05` family | walk left | bank 13 tiles `4..7` |
| `0x09` | idle/right | bank 13 tile `8` |
| `0x0A` | idle/left | bank 13 tile `9` |
| `0x0D` | fire/right | bank 13 tile `12` |
| `0x0E` | fire/left | bank 13 tile `13` |
| `0x0F/0x10` | jump/fall frames | bank 13 tiles `14/15` |

The runtime now tracks facing, walking time and a short firing hold time and uses
those values to select the source-derived sprite frame.

## Enemy / walker animation

Previous passes found that ordinary actors use 0x20-byte records with a frame
counter at `DS:34D6 + slot*0x20`, direction at `DS:34E2 + slot*0x20`, and sprite
selection at `DS:34E0 + slot*0x20`.  The EXE walking counter uses the ranges
`0x01..0x13` and `0x15..0x27` for opposite horizontal directions.

The prototype now extracts common walker map codes into runtime entities instead
of baking them into the static background:

| Map code | Decoded visual family | Implemented loop |
| --- | --- | --- |
| `0x65` | bank 2 tile 16 | right `16..19`, left `20..23` |
| `0x75` / `0x76` | bank 2 tile 8/12 family | right `8..11`, left `12..15` |
| `0x6E` | bank 2 tile 32 family | right `32..35`, left `36..39` |

These actors walk horizontally, turn around on body collision, and also turn at a
missing floor cell ahead.  This matches the simple left/right walker behaviour
visible in many levels, while keeping the exact per-actor EXE dispatch recovery
as a future task.

## Controls

Default level controls now follow the requested layout:

- Space = jump
- Ctrl = fire
- Left/Right or A/D = horizontal movement

World-map Space/Enter continues to enter a level.  Ctrl firing uses the decoded
player firing frames and creates a simple projectile when the current ammo count
is non-zero; ammo pickups already add shots in the runtime prototype.

## Still open

The next EXE-level improvement is to recover the exact actor initialisation table
that maps every map code to a specific actor state/type and speed.  The current
walker set is based on source-derived decoded bank/tile families and the recovered
horizontal actor model, but it is not yet a full actor dispatch clone.
