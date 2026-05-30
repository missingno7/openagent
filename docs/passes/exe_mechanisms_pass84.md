# Pass 84 - exact static fall probes for solid and one-way cells

## Symptom

In episode 1 level 3, the player could run left from the `DON'T FEED THE FISH`
sign and catch the blue block edge below. In the DOS game the same late edge
contact falls through.

The relevant map data is:

```text
raw 0xEB at (5,3)  decorative sign / foreground redraw cell
raw 0xD2 at (2,4)  composite blue block
```

Raw `0xD2` writes foot-only runtime cells at `(1,3)` and `(2,3)`. Its visible
top is a one-way `+0x1CD` surface, not a body-solid `+0x1CC` wall.

## ASM findings

Normal falling at `SAM1:0xB8B3..0xBA49` has a dedicated static-grid probe path.
It is not the generic four-corner body helper:

1. Apply the complete table displacement to player Y.
2. Probe body byte `+0x1CC` at `(x+3, y+16)` and `(x+12, y+16)`.
3. If `DS:34EA <= 0x0A`, skip the one-way path.
4. Probe foot byte `+0x1CD` at `(x+3, y+16)` and `(x+12, y+16)`.
5. If a foot cell is present, reject it when either `(x+3, y+7)` or
   `(x+12, y+7)` already sees foot byte `+0x1CD`.
6. Accepted landings align player Y down to a 16-pixel boundary.

The `y+7` rejection is the important edge behavior. It prevents a player who is
already too far through a one-way cell from being snapped generously back onto
its top.

## Runtime change

`move_player_fall_tick()` now uses a separate `player_fall_static_blocked()`
path that mirrors those probes. The broader `player_landing_y()` helper remains
only for reconstructed pixel-granular interactions such as the special barrel
fallback.

Dynamic moving-platform and barrel-top crossings remain separate from the
static runtime grid. Dynamic actor-backed body collision is also kept separate
until those original actor/player overlap branches are isolated.

## Verification

Targeted probes against the actual episode 1 level 3 runtime collision grid:

```text
0xD2 late edge overlap -> falls through
0xD2 genuine top crossing -> lands
0x62 dynamic platform crossing -> lands
```
