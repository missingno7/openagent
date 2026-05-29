# Pass 21 - retracting spike traps (bank 4 tiles 20..35)

This pass corrects the interpretation of the bank-4 spike tiles.  They are not
background animation frames.  Raw map bytes create actor records and the actor
state machine selects the visible tile.

## Raw map bytes

From the SAMLEV/Camoto mapping used by the project:

- raw `0x3F` starts as bank 4 tile 24 in the static atlas, but the EXE creates a
  floor spike actor.
- raw `0x41` starts as bank 4 tile 32 in the static atlas, but the EXE creates a
  ceiling spike actor.

## EXE initialization

In `SAM1_unpacked_linear_8086.asm`:

- raw `0x3F` token branch around `0x13A75` creates an actor slot and sets:
  - `DS:34E0 = 0x01B3` idle object
  - `DS:34D8 = 0x1E` period
  - `DS:34DA = random(0x1E)` initial timer offset
  - `DS:34E8 = 0x11` floor-spike behaviour state
- raw `0x41` token branch around `0x13B9B` creates the same actor shape but sets:
  - `DS:34E8 = 0x12` ceiling-spike behaviour state

So the different timings observed in episode 1 level 3 are not an X/Y modulo
pattern in the map.  The EXE randomizes `34DA` during level parsing.  The runtime
uses a deterministic hash of `(code, x, y)` to keep reloads reproducible while
preserving the intended phase staggering.

## EXE update logic

Actor dispatch around `0x6FBB..0x7041` handles state `0x11`:

```text
34DA++
local = 34DA - 34D8
if local >= 0:
    34E0 = 0x01D7 + (local >> 2)
if 34DA == 0x3C:
    34DA = 0
    34E0 = 0x01B3
call draw/damage helper 0x53C4 at actor_y + 8
```

Actor dispatch around `0x704C..0x70D2` handles state `0x12`:

```text
34DA++
local = 34DA - 34D8
if local >= 0:
    34E0 = 0x01DF + (local >> 2)
if 34DA == 0x3C:
    34DA = 0
    34E0 = 0x01B3
call draw/damage helper 0x53C4 at actor_y - 8
```

The visual ids map to the decoded bank-4 tile ranges:

- `0x01D7..0x01DE` -> bank 4 tiles `20..27` (floor spikes)
- `0x01DF..0x01E6` -> bank 4 tiles `28..35` (ceiling spikes)

## Implementation

- Added spike actor constants to `openagent/exe_actor_mechanics.py`.
- Added `SpikeTrap` entities and extraction of raw `0x3F` / `0x41` in
  `openagent/entities.py`.
- Added runtime tick update, drawing and provisional damage collision in
  `openagent/runtime.py`.
- Added these raw codes to dynamic mission codes so the original static tile is
  not baked into the background while the actor animation runs.

The damage helper is still approximate: the EXE calls `0x53C4` with the spike
position, so the prototype marks frames after the first emerging frame as
harmful.  The exact damage/lives routine is still a future extraction target.
