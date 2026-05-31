# Pass 127 — raw 0xA7 barrel push chunk and pushed-off-edge fall step

## Goal

Recheck the raw `0xA7` barrel's ordinary push and pushed-off-edge fall.  The
runtime was still mixing two different motion systems:

- the **player** horizontal/vertical system (`0x532D` and `DS:34AF`), and
- the **actor** record system (`DS:34E2/34E4` direction plus `DS:34E6` speed).

The user observation was that even a tiny player tap moves the barrel in visible
chunks of roughly four pixels.  Treat that as a testcase, not as proof.  The ASM
question is whether a barrel push/fall should be tied to the player's current
1/2/4px substep or to an actor-style speed slot.

## ASM evidence used

`SAM1:0x532D..0x53C0` is still the normal **player** horizontal acceleration
helper.  It can return 1, 2, 4, or speed-bonus 8 pixel steps for the player.
That does not by itself prove the same substep should be applied to a raw actor.

The actor-family prelude around `SAM1:0x81C8..0x8288` computes candidate actor
positions from the actor record fields:

- `DS:34E2` horizontal direction,
- `DS:34E4` vertical direction,
- `DS:34E6` actor speed,
- `DS:34CE/34D0` current actor X/Y.

The arithmetic there is candidate `x/y ± DS:34E6`, not player `DS:681E/DS:34AF`.
Several decoded helper/spawn paths already pass or store small integer actor
speeds independently of the player motion tables.  The best concrete nearby
example remains helper `0x5784` for projectiles, where the stationary launchers
call it with speed `0x04`.

The exact raw-`0xA7/state 0x1388` store for “pushed over an edge and now falling”
is still not fully isolated.  The evidence is therefore **partial**, but it is
strong enough to remove the unsupported use of the player's `DS:34AF` gravity
byte table from barrel fall.

## Python behavior change

Added `BARREL_ACTOR_STEP_PX = 4` in `openagent/game_constants.py` and used it in
two places:

1. `try_push_barrel()` now applies a raw barrel push as `step * 4`, not as the
   player's current one-pixel substep from `move_axis_pixels()`.
2. `update_barrels_tick()` now advances an unsupported raw barrel downward by the
   same actor step through `move_barrel_vertical()`, instead of indexing the
   player `PLAYER_VERTICAL_STEP_TABLE`.

`move_barrel_vertical()` still moves pixel-by-pixel internally so it cannot skip
a landing surface.  The actor step only controls the maximum attempted vertical
movement for that actor tick.

## Why this matters

Before this pass, a barrel pushed off an edge immediately used
`PLAYER_VERTICAL_STEP_TABLE[1] == 8`, so the first unsupported barrel tick fell
by eight pixels.  That was inherited from player falling and was not backed by a
raw-barrel ASM store.

Now a short tap can move the player by one pixel while the barrel itself moves by
a four-pixel actor chunk, matching the observed chunked push feel and the actor
speed-slot model better.

## Tests

Updated:

- `tools/check_barrel_player_interaction.py`
  - first side push now expects a 4px barrel displacement;
  - restored wall-release barrels are verified as ordinary pushable actors with
    the same 4px push step.
- `tools/check_barrel_vertical_fall.py`
  - pushed-over-edge support loss now expects the 4px horizontal push candidate;
  - added a regression that an unsupported raw barrel falls by
    `BARREL_ACTOR_STEP_PX`, not by `PLAYER_VERTICAL_STEP_TABLE[1]`.

## Remaining gap

This pass deliberately does **not** claim that pushed-off-edge timing is fully
proven.  The exact `0x1388` caller/store that turns a supported pushed barrel
into a falling actor still needs a focused ASM trace or DOSBox pixel capture.
What this pass fixes is the unsupported coupling to the player gravity table and
makes the current approximation explicit, named, and test-covered.
