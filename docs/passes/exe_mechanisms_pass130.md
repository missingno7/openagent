# EXE mechanisms pass 130: same-tick vertical alignment before horizontal doorway probe

Focus: investigate the one-tile opening case reported from playtesting.  When the
player jumps or falls against a wall with a single passable 16px cell, the Python
runtime could reject the horizontal move and let the player fall even though the
original game can enter the opening once the vertical position lines up.

The user observation is treated only as a testcase.  The implemented change is
based on the ASM collision rectangle and the traced vertical movement phase, while
the exact outer player-control wrapper order is still marked as a remaining gap.

## ASM findings

### Shared B7D9 collision rectangle

`SAM1:0xB7D9..0xB8B0` is the shared player destination collision helper used by
mission movement and also by level-0 top-down movement.

It tests the runtime body byte `+0x1CC` at four corners of the player-origin
rectangle:

- left sample: `DS:34EE + dx + 3`
- right sample: `DS:34EE + dx + 12`
- top sample: `DS:34F0 + dy`
- bottom sample: `DS:34F0 + dy + 15`

So the gameplay body is 10px wide by 16px tall, anchored at the player origin.  A
single 16px opening only works if the Y origin is aligned so both vertical samples
land inside that same map row.

### Vertical phase

`SAM1:0xBC0E..0xBD8A` owns the normal vertical side of player movement:

- when `DS:6EC1` is clear it calls the fall path `SAM1:0xB8B3..0xBA49`, which
  increments/caps `DS:34EA`, uses the `DS:34AF` step table, probes the body/foot
  bytes, and snaps `DS:34F0` to a 16px boundary on landing/collision;
- when a jump is accepted it sets `DS:6EC1`, resets `DS:34EA`, and immediately
  enters the table-driven upward phase;
- upward movement reads the same `DS:34AF` table, negates the step, calls `B7D9`
  with `dx=0`, `dy=-step`, and subtracts the step from `DS:34F0` when clear.

### Ordering conclusion

The old Python order applied horizontal movement before the vertical phase.  That
means a player one pixel below a one-tile opening could be rejected by the lower
corner in `B7D9` before the same tick's jump ascent or landing snap aligned the
origin to the passage.

Pass 130 changes the Python runtime so the BC0E-style fall/jump phase is applied
before the later horizontal destination probe for the same tick.  This is an
ASM-anchored ordering reconstruction, not a fully closed wrapper trace: the exact
outer overlay caller sequence around the player-control routines still needs to
be named from `0x520:0x68F5 / 0x520:0x6A0E`.

## Python changes

`openagent/runtime.py::update_player_tick` now:

1. reads input and advances the horizontal hold counter,
2. computes the horizontal step for this tick but does not apply it yet,
3. applies the BC0E-style fall/jump phase,
4. updates speed-bonus timing,
5. applies the horizontal `B7D9` destination probe with the already-aligned Y.

This preserves the horizontal step ramp for the tick while making same-tick Y
alignment visible to the horizontal probe.

## Regression check

Added `tools/check_player_motion_accuracy.py`.

The test builds a synthetic wall column with one clear 16px opening.  It first
shows that the raw horizontal helper rejects movement at `y=49` because the lower
corner samples the blocked row below the opening.  Then it runs the real player
tick while holding jump+left: the jump phase moves the origin to `y=48` first,
and the same tick's horizontal movement is accepted into the opening.

`tools/check_handoff.py` now runs the new probe.

## Remaining gaps

- Fully trace the outer player-control wrappers around `BC0E` and the horizontal
  control path so this ordering can be upgraded from guarded reconstruction to a
  named ASM phase.
- Capture DOSBox pixel references for the reported one-tile opening case.
- Add nearby probes for ceiling hits, landing snaps, wall approach while falling,
  and actor-backed solids.
