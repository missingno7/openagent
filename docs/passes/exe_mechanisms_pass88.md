# Pass 88 - raw `0x77` teleporter re-audit: alignment, rearm gate, idle top animation, warp effect

## ASM evidence

The interaction branch for the bottom pad runtime visual is at `SAM1:0xD48B..0xD5E8`:

- it compares the touched runtime visual against `0x00B7`;
- it aligns the touched pad X to a 16 px boundary and requires `DS:34EE` (player X) to be within `+/-2 px` of that boundary (`0xD493..0xD4CB`);
- it refuses to arm while `DS:69E0 != 0` (`0xD4CE..0xD4D5`);
- it plays sound `0x17`, scans the runtime map row-major for another `0x00B7`, skipping the source pad;
- it stores `DS:69E4 = (target_col - 1) << 4` and `DS:69E6 = (target_row - 1) << 4`;
- it probes runtime byte `+0x1CC` one row below the target; if that byte is non-zero it adds `+3` to `DS:69E4`, otherwise it subtracts `3`;
- it sets `DS:69E0 = 1`, `DS:69E2 = 0x13`, and `DS:69B4 = 1`.

The main loop branch at `SAM1:0x2014..0x2039` decrements `DS:69E2`, requests the coordinate copy when it reaches zero, and clears `DS:69E0` only when the timer reaches `-0x13`.

The draw branch at `SAM1:0x21E4..0x2254` renders the teleport effect while `DS:69E0` is active:

- positive half: one-based tile `0x28 - (DS:69E2 / 5)`;
- negative half: one-based tile `0x28 + (DS:69E2 / 5)`;
- decoded zero-based atlas tiles are bank 10 `36..39`.

The raw `0x77` composite object writes upper runtime visual `0x00B3` and bottom runtime visual `0x00B7`.  The upper cel is the bank-10 `28/29` two-frame idle pair, while the bottom pad remains bank-10 tile `32`.

## Runtime fixes

- Replaced the broad center-based mission-pad trigger with the ASM-style `player.x` vs tile-origin `+/-2 px` gate.  The prototype overworld teleporter path keeps its previous looser centering rule.
- Kept an explicit destination release gate until the player collision footprint leaves the destination pad.  This prevents a mission teleporter from ping-ponging while still allowing the player to walk out normally.
- Changed target X nudge to the recovered ASM rule: probe `+0x1CC` one row below the target pad, then use `+3` if solid else `-3`.
- Raw `0x77` is no longer baked into cached mission foreground/background layers.  It is drawn live as:
  - upper tile: bank 10 `28/29`, fixed-tick two-frame loop;
  - lower pad: bank 10 `32`;
  - active warp effect: bank 10 `36..39` over the player, using `DS:69E2 / 5` timing.
