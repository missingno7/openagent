# Pass 128 — raw 0xA7 falling barrel side-push lock

## Goal

Focus on the pushed-off-edge phase of the raw `0xA7` barrel.  The playtest
observation was that once the barrel leaves support and starts falling, holding
against it in the original DOS game does not keep pushing it sideways into later
columns.  Treat that as a testcase, then check whether the current Python model
still allowed side pushes during fall.

## ASM evidence used

The exact store/caller for the raw-`0xA7` pushed-off-edge transition is still not
fully isolated, so this pass does not claim a complete state proof.  The useful
ASM evidence is the actor-family prelude at `SAM1:0x81C8..0x8288`:

- candidate X is computed from `DS:34CE` plus/minus `DS:34E6` when horizontal
  direction `DS:34E2` is active;
- candidate Y is computed separately from `DS:34D0` plus/minus `DS:34E6` when
  vertical direction `DS:34E4` is active;
- this is separate from the player movement helper `SAM1:0x532D` and separate
  from the player vertical byte table `DS:34AF`.

That supports keeping pushed-off-edge fall as a separate vertical actor phase,
not as “still the same side-pushable body plus gravity”.

## Python bug found

Pass 127 made barrel push/fall use a named 4px actor step, but the barrel stayed
eligible for `player_touching_barrel()` while unsupported.  In a multi-pixel
player movement tick, this meant:

1. a push could move the barrel off the support tile;
2. the barrel was marked `grounded = False`;
3. later pixels in the same player tick, or later ticks while the barrel was
   falling, could still call `try_push_barrel()` and move it horizontally again.

That is the direct reason the port could let the falling barrel drift out of the
single tile column just past the ledge.

## Runtime change

Added explicit raw-barrel fall locking:

- `PushableBarrel.falling_locked` is set when a successful side push leaves the
  barrel with no floor support.
- `update_barrels_tick()` also sets the lock while the barrel is unsupported.
- `player_touching_barrel()` skips falling-locked barrels, so side contact no
  longer calls `try_push_barrel()` during the fall.
- Falling barrels still participate in dynamic body collision, so the player
  cannot simply keep pushing through them as if they were wall-release
  pass-through bodies.
- The lock is cleared when `move_barrel_vertical()` / `update_barrels_tick()`
  lands the barrel on floor support.

This keeps the barrel's X coordinate fixed for the unsupported fall column until
it lands, matching the observed “cannot influence it during the drop” behavior.

## Tests

Extended `tools/check_barrel_vertical_fall.py` with checks that:

- an already falling barrel overlaps the player but is not returned by
  `player_touching_barrel()`;
- side movement into a falling barrel blocks the player rather than pushing the
  barrel horizontally;
- a multi-pixel player tick that pushes the barrel over the edge cannot push it
  again later in the same tick;
- after landing, the falling lock clears and the barrel becomes ordinary
  pushable `0xA7/state 0x1388` again.

## Remaining gap

The exact raw-`0xA7` unsupported transition store in the ASM is still open.  The
current behavior is a guarded reconstruction from the actor-direction separation
at `0x81C8..0x8288` plus DOS observation, now protected by regression tests.
