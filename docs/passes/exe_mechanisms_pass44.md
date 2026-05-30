# Pass 44 - state 0x29 money bag actor and actor-gap refresh

This pass continues the special actor table cleanup after passes 42 and 43.
The remaining high-value unpromoted entry was raw `0x5B`, previously treated as
an ordinary static money-bag score pickup.

## raw `0x5B` / object `0x01B3` / state `0x29`

The actor dispatcher branch at `SAM1:0xB0EF..0xB596` handles behavior state
`0x29`.

Important details from the branch:

- The idle actor starts as object `0x01B3`.
- `SAM1:0xB109..0xB144` compares player deltas against a tight roughly `±8 px`
  X/Y trigger box.
- On trigger, `SAM1:0xB146..0xB191` scans upward in 16 px steps until it reaches
  a body-collision cell, then rewrites the actor to object `0x026B`.
- The same rewrite stores `DS:34E6 = 8` and `DS:34E4 = 1`.
- The moving branch at `SAM1:0xB1B4..0xB309` checks the actor footprint against
  runtime body/floor collision and advances the Y coordinate downward in 4 px
  steps when clear.
- The collection branch at `SAM1:0xB4A4..0xB596` checks another tight overlap and
  adds `0x1388` to the score, i.e. **5000 points**, then rewrites the slot to an
  explosion/score state (`state 0x1389`, object `0x00AC`).

Runtime now promotes raw `0x5B` to a dynamic actor instead of baking it into the
static layer.  The implementation keeps the same high-level state split:

1. idle trigger object `0x01B3`,
2. falling object `0x026B`,
3. 5000-point collection + impact/score popup.

The exact two draw-helper calls after the EXE collection rewrite still need a
later visual-only pass.  Gameplay-wise, the important correction is that `0x5B`
is no longer consumed as a simple 1000-point static pickup.

## Actor gap report refresh

`docs/derived_mechanics/pass27_actor_gap_report.json` was refreshed so the
entries implemented in passes 42, 43 and 44 no longer appear as false negatives:

- `0x75` state `0x23` contact bomb,
- `0x76` state `0x24` upward laser emitter,
- `0x5B` state `0x29` money bag actor,
- `0x40` state `0x2B` animated special,
- `0xD4` state `0x2C` animated special,
- `0x78` state `0x2C` animated contact hazard.

This makes the gap report useful again as a TODO source instead of pointing at
already-filled holes.
