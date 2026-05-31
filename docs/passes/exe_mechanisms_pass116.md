# EXE Mechanisms Pass 116 - Raw 0xA7 Barrel Vertical Fall

## Why this pass exists

The runtime still had a leftover approximation in the raw `0xA7` pushable-barrel
fall path.  When a barrel was pushed off a ledge, the gravity step reused the
same broad 16x16 body collision helper used for horizontal pushes.  That meant a
barrel whose AABB overlapped a side wall could stop during a vertical fall, or
look as if it was caught by an adjacent solid tile.

That does not match the original feel: after the barrel is released into the
falling actor state, it drops straight down at the same X coordinate.

## ASM evidence

The raw `0xA7` branch remains the same actor-family evidence documented in
passes 32 and 37:

- `SAM1:0x82E3..0x8742` handles the special `0x1388/0x1389` actor states around
  raw `0xA7` rather than treating the object as a plain map-solid tile.
- `SAM1:0x8335` and `SAM1:0x84B3` rewrite the actor state to `0x1389`.
- `SAM1:0x83C4..0x848A` uses a shrunken player/actor overlap test for the
  horizontal/player interaction branch.
- The falling actor path keeps the actor in its slot and updates its stored
  coordinates; vertical support is resolved separately from the horizontal
  broad-body push test.

The important runtime implication for this pass is conservative: horizontal
pushes still need broad body collision, but the vertical gravity step must not
turn adjacent side-body contact into a landing/blocking event.

## Runtime change

`move_barrel_vertical()` now:

- keeps `barrel.x` unchanged,
- checks only the landing/foot probes through `barrel_landing_y()`,
- lands on floor/foot-solid cells or other barrels,
- no longer calls `barrel_collides()` after each 1px downward step.

`try_push_barrel()` still calls `barrel_collides()` for horizontal pushes, so
wall blocking during pushing is preserved.  The change is limited to gravity.

## Regression test

Added:

```bash
python tools/check_barrel_vertical_fall.py
```

The test sets up a barrel that overlaps a side-solid cell under the broad AABB.
`barrel_collides()` intentionally sees the side contact, but
`move_barrel_vertical()` must still move the barrel down and keep the X
coordinate fixed.  A second case confirms that real floor probes still land the
barrel.
