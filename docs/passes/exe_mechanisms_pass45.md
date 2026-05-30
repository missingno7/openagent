# EXE mechanisms pass 45 — bank-12 two-high shooters 0x56/0x58

This pass fills another first-pass actor gap from the special actor table and
corrects the collision footprint used by several composite actors.

## Composite actor footprint correction

The runtime hitbox was still treating raw `0x24`, `0x56`, and `0x58` as if they
were two tiles wide.  The decoded sprite composition and EXE-style actor origins
match a vertical pair instead:

- raw `0xAE`: horizontal pair at `(x-16, y)` and `(x, y)`.
- raw `0x24`, `0x56`, `0x58`: vertical pair at `(x, y-16)` and `(x, y)`.

This matters for player contact, bullet hits, floor probes, and edge reversal.
The floor-ahead test now uses the decoded actor rectangle, so two-high actors no
longer probe from the wrong side of a fake two-wide footprint.

## raw 0x56 / object 0x0321 / state 0x1E

The update branch starts at `SAM1:0x8AD1`.  The firing sub-branch around
`SAM1:0x8D45..0x8D7C` calls projectile helper `0x5784` with:

- object `0x0339`,
- speed `4`,
- direction from the actor direction field,
- then reloads the timer with `0x46`.

Runtime implementation:

- promoted from first-pass walker to `state1e_shooter`,
- keeps the two-high bank-12 footprint,
- moves at the special-table speed, `2 px/tick`,
- fires horizontally when the player overlaps the decoded vertical actor span
  and is in front of the actor,
- reloads with `0x46` actor ticks after firing.

## raw 0x58 / object 0x0331 / state 0x1F

The update branch starts at `SAM1:0x905C`.  The firing sub-branch around
`SAM1:0x9280..0x92AA` calls projectile helper `0x5784` with:

- object `0x033B`,
- speed `4`,
- direction from the actor direction field.

Runtime implementation:

- promoted from first-pass walker to `state1f_shooter`,
- keeps the two-high bank-12 footprint,
- moves at `2 px/tick`,
- uses the special-table `60` tick period,
- fires horizontally when the player overlaps the decoded vertical actor span
  and is in front of the actor.

## Remaining caveat

The helper object ids (`0x0339`, `0x033B`) and speed are taken from the EXE.  The
current visual mapping still reuses the already-decoded horizontal projectile
sprite pair from bank 1 tiles `38/39`.  If a later object-id-to-sprite pass finds
a distinct projectile visual for `0x0339` or `0x033B`, only that visual mapping
should change; the actor state, timer, and helper call are now anchored to the
EXE branch.
