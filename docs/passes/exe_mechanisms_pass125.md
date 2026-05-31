# Pass 125 — raw 0xA7 wall-release timing and clearance

## Goal

Correct the pass-124 wall-release timing for the pushable raw `0xA7` barrel.
The reported DOS behavior is that after the barrel is pushed hard against a
wall, the player can pass through its body and the barrel retreats from the wall
before the player's full sprite visually reaches the wall.  Pass 124 waited for
a live front-wall body probe, which made the handoff too late.

As usual, the player observation is a testcase, not a source of truth.  The ASM
source of truth used in this pass is the already decoded raw-`0xA7`
player/actor overlap rectangle at `SAM1:0x83C4..0x842F`.

## ASM evidence used

`SAM1:0x83C4..0x842F` does not test full 16px sprite boxes.  It tests the same
10px horizontal interval for the player and actor:

- actor interval: `actor_x + 3 .. actor_x + 12`
- player interval: `player_x + 3 .. player_x + 12`

The destructive branch at `SAM1:0x848A..0x84E9` is still explicitly **not** used
for wall-release.  It plays sound `0x04`, adds `+0x03E8`, rewrites the visible
object to `0x00AA`, and enters state `0x1389`, which is the wrong behavior for a
wall-blocked barrel.

I still did **not** isolate the exact ASM caller/store that performs the
wall-blocked free-side restoration.  This pass therefore replaces the pass-124
live-wall-probe heuristic with a tighter reconstruction directly derived from
the known ASM overlap rectangle.

## Python behavior change

`update_wall_release_barrels()` no longer waits for
`player_front_wall_for_barrel_release()`.

For a right-wall push, it restores the barrel when:

```text
player_x + 12 >= barrel_x + 12
```

That is, when the player's leading shrunken edge reaches the barrel's leading
shrunken edge.  The left-wall case mirrors this with `x + 3`.

`restore_wall_release_barrel_to_free_side()` now restores the barrel just outside
the same shrunken rectangle instead of moving it by a full 16px tile:

```text
right-wall case: barrel_x + 12 < player_x + 3  -> barrel_x = player_x - 10
left-wall case:  player_x + 12 < barrel_x + 3  -> barrel_x = player_x + 10
```

This matches the observed small retreat, roughly 10/11 pixels, and happens while
the player's full 16px sprite is still just short of the wall.

## Tests

`tools/check_barrel_player_interaction.py` now covers:

- wall-blocked push still does not enter the destructive score/sound state;
- wall-release remains body-pass-through and top-solid;
- restoration happens at the shrunken leading-edge crossing, not at the later
  pass-124 wall-probe tick;
- the free-side candidate uses shrunken-rectangle clearance (`player_x ± 10`),
  not full-tile clearance (`player_x ± 16`).

## Remaining gap

The exact ASM caller/store for the wall-blocked free-side restoration is still
open.  Next useful step is either a DOSBox pixel/tick capture of this exact
scenario or deeper tracing of the player push path that leads into the raw
`0xA7/state 0x1388` actor branch without using the destructive `0x848A` path.
