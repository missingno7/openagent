# EXE Mechanisms Pass 50 - raw 0x7F / state 0x06 contact floater

## Target

Raw `0x7F` had been treated as a normal ground walker because the special actor
table identifies it as:

- object id `0x0261`
- state `0x06`
- step `2 px/tick`
- timer field `2`
- bank 5 tile family `8..11`

That first implementation reused the generic walker rule, including the
floor-ahead/ledge probe.

## ASM check

The relevant dispatcher block is `SAM1:0x6864..0x6A21`.

Important differences from a ground walker:

- the branch probes the runtime collision table's body byte `+0x1CC` at the
  candidate side/top-bottom points;
- on blocked side collision it negates `DS:34E2`, i.e. reverses direction;
- it increments the actor frame counter and wraps the `0x01..0x13` visible
  range;
- it stores the accepted candidate position back into `DS:34CE`;
- it calls helper `0x53C4` every tick, matching the narrow player-contact hazard
  path used by other harmful actors;
- there is no floor-ahead / support-under-foot probe in this branch.

So raw `0x7F` should not turn around merely because the tile below the next
step is empty.  It behaves like a side-collision contact floater/hazard, not a
ledge-aware ground walker.

## Runtime changes

- Added `STATE06_CONTACT_FLOATER_CODE = 0x7F`.
- Extracted raw `0x7F` as `Enemy(kind="state06_contact_floater")`.
- Movement now reverses only on body collision / level edge, not on missing
  floor support.
- Contact with the player now calls the same `hurt_player()` path as other
  `0x53C4` contact hazards.
- The visual mapping remains bank 5 tiles `8..11`, mirrored when moving left.

## Remaining caveat

The ASM branch contains an extra `object 0x0271` sub-state after repeated hits
or state changes.  It is not yet promoted to a separate runtime visual/state;
this pass only fixes the confirmed movement and contact-hazard semantics for
raw `0x7F` / object `0x0261` / state `0x06`.
