# Pass 51 - paired teleporters (`0x77` / runtime visual `0x00B7`)

## Evidence from map/runtime tables

Raw map byte `0x77` is used in both mission maps and overworld maps.  The atlas mapping is the same in both tables:

- top tile: bank 10 tile 28 at `(x, y-1)`
- bottom/pad tile: bank 10 tile 32 at `(x, y)`

The reconstructed runtime collision table maps the bottom pad to visual `cA = 0x00B7`; the top tile is `cA = 0x00B3` and has body collision.

Observed `0x77` occurrences include paired overworld teleporters:

- episode 1 world: `(24,5)` <-> `(35,22)`
- episode 2 world: `(36,8)` <-> `(23,12)`
- episode 3 world: `(7,11)` <-> `(26,21)`

Mission levels also contain multiple `0x77` pads, including rooms with more than one pair; the EXE resolves the target by scanning for another pad, not by a separate pair-id table.

## Evidence from ASM

Interaction dispatcher branch:

- `SAM1:0xD48B` compares the active runtime visual with `0x00B7`.
- The branch requires the player to be tightly aligned with the pad before triggering.
- It skips if teleport state `DS:69E0` is already active.
- It plays sound `0x17`.
- It scans the runtime map for another cell whose `+0x1CA` visual is also `0x00B7`, skipping the current source pad.
- When a target pad is found, it stores:
  - `DS:69E4 = (target_col - 1) << 4`
  - `DS:69E6 = (target_row - 1) << 4`
- It then nudges target X by `+3` or `-3` based on a body-collision probe at the destination.
- Finally it sets:
  - `DS:69E0 = 1`
  - `DS:69E2 = 0x13`
  - `DS:69B4 = 1`

Main loop branch:

- `SAM1:0x2014` checks `DS:69E0`.
- While active, it decrements `DS:69E2`.
- When `DS:69E2 == 0`, it sets the pending warp flag `DS:69D8`.
- When `DS:69E2 == -0x13`, it clears the active teleport state.
- When `DS:69D8` is handled, it copies `DS:69E4/DS:69E6` into the player coordinates and updates camera position.

There is also a draw branch around `SAM1:0x21E4..0x2254` that renders a teleport effect while `DS:69E0` is active.  This pass implements the mechanics; the visual warp effect is still approximate/not fully reconstructed.

## Runtime implementation

- Added raw constant `TELEPORTER_CODE = 0x77` and semantic entry.
- Mission and world maps both scan `0x77` cells.
- Touching/alignment on the bottom pad triggers teleport only if no teleport is already active.
- Target pad is selected by row-major scan for the first other `0x77`, matching the ASM scan-style behavior.
- Teleport freezes control and starts a 19 tick timer.
- At timer `0`, player position is changed to the target pad position.
- Teleport remains active for another 19 ticks as cooldown, preventing instant re-trigger ping-pong.
- Target X uses the observed `±3 px` nudge and chooses the first non-colliding side in the reconstructed runtime collision model.
