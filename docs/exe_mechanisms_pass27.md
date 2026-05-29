# Pass 27 — special actor coverage and timed bank-3 beam traps

This pass continues the rule used in the previous passes: when a raw mission map
code is present in the EXE special actor table, it should be promoted to a
runtime actor instead of being baked into the static level bitmap.

## New EXE-derived mechanism: raw `0x3B` / `0x3E` timed beam traps

The special actor table at `CS:3A59` contains two entries that were still being
rendered statically:

| raw | initial object | state | timer |
|---:|---:|---:|---:|
| `0x3B` | `0x01B3` | `0x0F` | `DS:34D8 = 0x1E`, `DS:34DA = random(0x1E)` |
| `0x3E` | `0x01B3` | `0x10` | `DS:34D8 = 0x1E`, `DS:34DA = random(0x1E)` |

The update dispatcher around `SAM1:0x6E81..0x6FB0` does the important part:

```text
state 0x0F:
  34DA++
  if 34DA >= 34D8:
      34E0 = 0x01AD + ((34DA - 34D8) >> 2)
  if 34DA == 0x2D:
      34DA = 0
      34E0 = 0x01B3

state 0x10:
  34DA++
  if 34DA >= 34D8:
      34E0 = 0x01B5 + ((34DA - 34D8) >> 2)
  if 34DA == 0x2D:
      34DA = 0
      34E0 = 0x01B3
```

So both traps have a 30-tick hidden delay, then a short 15-tick active window
split into four frame phases.  Like spike traps, the initial phase is random in
the original game.  The runtime uses a deterministic hash of `(code, x, y)` so
editor reloads are stable while still desynchronizing the traps.

Current visual mapping uses the decoded bank-3 composite tiles:

- `0x3B` vertical trap: bank 3 tiles `26`, `28`, `27` as the beam extends upward.
- `0x3E` horizontal trap: bank 3 tiles `33`, `36`, `32` as the beam extends left.

This is still a first runtime interpretation of the draw helper `0x53C4`: the
EXE clearly gives the object-id/timer state machine above, while the exact
object-id to decoded-bank/tile lookup should be folded into a generated table in
a later pass.

## Actor coverage report

Added `tools/extract_sa_pass27_actor_gap_report.py`, producing
`docs/derived_mechanics/pass27_actor_gap_report.json`.

The report marks which `CS:3A59` special actor entries are already promoted to
runtime entities and which ones still need state-specific dispatch work.  This is
intended to prevent future passes from guessing blindly — new mechanics should be
chosen from this TODO list or from a newly discovered dispatch branch.

## Runtime implementation

- Added `BeamTrap` entities.
- Added EXE timer constants and helper functions to `openagent/exe_actor_mechanics.py`.
- Added `0x3B/0x3E` to dynamic mission codes so they are no longer baked into the
  static level image.
- Added drawing and first damage collision for active beam phases.
- Added the generated actor-gap report.
