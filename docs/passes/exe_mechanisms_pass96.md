# Pass 96 - object-0x72 laser state split and pass-95 correction

## Scope

This pass re-opened the projectile dispatcher around `SAM1:0xA239..0xA70C`
because pass 95 correctly identified the helper rewrite
`0x00C7 -> object 0x72/state 0x89`, but then attributed the later hard-death
rectangle to the wrong state.

## ASM evidence

### Helper `0x5784` object mapping

The object mapping in helper `0x5784` is:

- `SAM1:0x5961..0x5990`: input object `0x0072` becomes state `0x25` and stores
  caller direction in `DS:34E4`.
- `SAM1:0x599A..0x59C3`: input object `0x00C7` is rewritten to object `0x0072`
  and becomes state `0x89`.

So both projectile families draw as object `0x72`, but they are not the same
behavior state.

### Dispatcher split

The dispatcher order is the important correction:

- `SAM1:0xA239` compares the actor state against `0x89`.
- If it is not `0x89`, execution jumps to `SAM1:0xA456` and tests for state
  `0x25`.

That means the direct death branch at `SAM1:0xA656..0xA70C` belongs to
state `0x25`, not state `0x89`.

### State `0x89` / ceiling-crawler beam

State `0x89` handles its own collision/redraw branch around
`SAM1:0xA241..0xA3E8`.  On the normal moving path it reaches
`SAM1:0xA439..0xA450`, pushes the beam coordinates, and calls helper `0x53C4`.

`0x53C4` is the generic narrow contact damage helper already used by other
contact hazards.  It decrements one life and starts the invulnerability window;
it only enters full death through the generic last-life path.

Runtime consequence: the ceiling-crawler beam should use a narrow 10x16 hitbox,
keep its actor slot after contact, and call generic `hurt_player()`, not direct
`kill_player()`.

### State `0x25` / ordinary object-0x72 up-laser

State `0x25` starts at `SAM1:0xA456`.  On the non-wall path it reaches
`SAM1:0xA607..0xA656` to update the Y position, then performs the rectangle
checks at `SAM1:0xA656..0xA6F2`.  On overlap it writes:

- `DS:69F5 = 1`,
- `DS:69F6 = 0x23`,
- and plays sound `0x16`.

Runtime consequence: raw `0x76` / state `0x24` emits object `0x72`, so its
upward laser is the direct hard-death version.

### Wall/solid impact policy

Both object-0x72 laser states use the foreground redraw/collision path rather
than the ordinary `0x1388/object 0x0187` wall spark.  The runtime now marks their
solid impact as a short invisible two-tick slot occupation instead of drawing the
large projectile spark.

The exact redraw-side effects around `SAM1:0xA2AF..0xA604` remain documented as
a future visual-accuracy task.

## Runtime changes

- Added explicit projectile metadata:
  - `narrow_hurt_on_hit`,
  - `keep_on_player_hit`,
  - `impact_visible_on_solid`,
  - `impact_ticks_on_solid`.
- Ceiling-crawler `0x00C7 -> object 0x72/state 0x89` now uses:
  - narrow 10x16 hitbox,
  - generic hurt policy,
  - keep-on-hit behavior,
  - invisible solid impact.
- Raw `0x76` up-laser `object 0x72/state 0x25` now uses:
  - narrow 10x16 hitbox,
  - direct hard-death policy,
  - keep-on-hit behavior,
  - invisible solid impact.
- Updated comments/constants that previously described state `0x89` as direct
  hard death.

## Intentional limitations

- The exact foreground redraw calls for object-0x72 collision are not yet
  visually rebuilt; the runtime only avoids the wrong large wall-spark.
- Projectile draw origin/frame cadence for object-0x72 lasers still needs a
  DOSBox/reference comparison.
