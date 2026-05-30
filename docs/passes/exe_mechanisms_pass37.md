# EXE Mechanisms Pass 37 - Pushable Barrel Falling

## Summary

The pushable barrel (`0xA7`, bank 6 tile 24) is not a static solid tile and it
is not only a horizontal pusher.  The original actor branch around
`SAM1:0x82E3..0x8742` keeps it in the actor slot system with object id
`0x00A7` and state transitions through `0x1388/0x1389`.

The previous runtime had the horizontal push/anti-stick part, but missed the
important implication: once pushed off a ledge, the barrel must continue as a
dynamic object and fall.

## Runtime Change

`PushableBarrel` now tracks:

- `grounded`
- `fall_ticks`

Every actor tick, barrels test for floor support under their foot probes.  If
the support is gone, they fall using the same fixed tick displacement table used
by the player movement model.  They land on runtime floor/body cells or other
barrels, and the player can still stand on the top edge.

This fixes the observed original-game behavior where a barrel can be pushed off
an edge instead of remaining suspended at the old Y position.

## Still Open

The exact `0x1388 -> 0x1389` animation/state timing still needs a narrower
decode.  The current implementation preserves the key gameplay invariant:
`0xA7` is a dynamic actor with gravity and special player overlap handling, not
a map tile.
