# Pass 22 — spike origin correction, satellite tile animation, 0x6E/0x7F actors

This pass corrects one bad coordinate interpretation from pass21 and adds two
actor/animation cases requested during play testing.

## Spike traps: draw origin

Pass21 correctly identified raw `0x3F` and `0x41` as actor slots rather than
static tiles:

- `0x3F`: floor spike, state `0x11`, bank 4 tiles `20..27`.
- `0x41`: ceiling spike, state `0x12`, bank 4 tiles `28..35`.
- both use actor period `0x1E` and cycle length `0x3C` ticks.

However, the decoded-coordinate renderer applied the EXE half-tile sprite-origin
adjustment as if the stored actor coordinate were still the original low-level
sprite origin. In the current editor/runtime coordinate system that made the
spikes draw 8 pixels too low. The runtime now shifts both variants up by half a
tile:

- floor spike draw Y: `cell_y * 16`
- ceiling spike draw Y: `cell_y * 16 - 16`

The active-frame and damage logic still uses the same `timer >= 0x1E + 4`
threshold from pass21.

## Rotating satellite: raw `0x23`

The rotating satellite is not related to the background-variant codes
`0x35..0x37`. It is a special actor entry in the table at `CS:3A59`:

- raw code `0x23`
- object id `0x0097`
- behaviour/state `0x20`
- timer period `3`

The decoded atlas maps the visible marker to bank 10 tile `0`; the adjacent
sprites `0..3` are the rotation frames. The renderer now animates `(10,0)` as:

```text
(10,0) -> (10,1) -> (10,2) -> (10,3)
```

with a 3 DOS-tick frame period.

## Raw `0x6E`: bank 2 tiles `32..35`

The previous runtime treated raw `0x6E` as an 8-frame two-direction actor:
`32..35` and `36..39`. The special actor table says `0x6E` is one actor record
with object id `0x0085`, step `2 px/tick`, behaviour `0x26`, and timer
`random(0x14)+0x1E`. The bank layout shows that tiles `36..39` are a different
blue actor family, not the opposite direction of `0x6E`.

The runtime now uses only bank 2 tiles `32..35` for `0x6E` and mirrors the tile
when the actor moves left.

## Raw `0x7F`: bank 5 tiles `8..11`

Raw `0x7F` is also in the special actor table:

- object id `0x0261`
- behaviour/state `0x06`
- speed `2 px/tick`
- timer period `2`
- random initial direction

The decoded atlas maps it to bank 5 tiles `8..11`. The runtime now extracts it
as a proper actor, runs it as a simple horizontal walker for now, and mirrors the
same four frames when travelling left.

The next worthwhile step is to follow behaviour states `0x06`, `0x20`, and
`0x26` in the actor dispatch loop, because those states likely contain the exact
projectile/damage or special-case movement behaviour that goes beyond this
visible walker prototype.
