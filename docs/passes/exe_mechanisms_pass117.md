# EXE Mechanisms Pass 117 - Tick Accuracy Ledger and Annotated ASM Map

## Why this pass exists

The project already had many useful notes: chronological pass logs, a mechanic
status registry, derived JSON/CSV facts, and a few focused smoke tests.  The
missing layer was a single map that answers this question:

> Which Python tick entrypoint is supposed to match which ASM branch, and what
> exactly is still guessed?

Without that layer, it was too easy to fix a local symptom while losing track of
whether the behavior was backed by ASM, a DOSBox observation, or a useful but
unproven reconstruction.

## Added files

- `docs/TICK_ACCURACY_LEDGER.md`
  - human-readable guide for tick-accurate work,
  - phase table for mission tick order, hard death, normal movement, raw `0xA7`
    barrels, overworld tick, animated decor/contact policy, and projectile/enemy
    contact policy,
  - consistent comment tags: `FACT`, `ASM`, `PY`, `VERIFIED`, `PARTIAL`, `HYP`,
    `GAP`, `TODO`, `WRONG_PREVIOUS_ASSUMPTION`.

- `docs/registry/tick_accuracy_ledger.json`
  - machine-readable phase ledger,
  - each phase links status, mechanic registry IDs, Python entrypoints, ASM refs,
    exact claims, blind spots, tests, and next actions.

- `tools/audit_tick_accuracy.py`
  - validates the tick ledger,
  - checks duplicate IDs, known status values, existing Python/doc/test paths,
    and known mechanic registry IDs.

- `dissassembly/annotated/README.md`
  - policy for annotated ASM working copies.

- `dissassembly/annotated/SAM1_tick_accuracy_excerpts.asm`
  - first commented ASM working file,
  - covers hard-death tick order, raw `0xA7` barrel state branch, level-0
    collision/movement, and raw `0x40` decorative state `0x2B`.

## Handoff integration

`tools/check_handoff.py` now runs:

```bash
python tools/audit_tick_accuracy.py
```

This means stale tick-ledger paths or unknown mechanic IDs fail the normal
handoff checks.

## Current biggest blind spots surfaced by the ledger

1. Raw `0xA7` horizontal/player overlap release is still reconstructed even
   though pass 116 fixed the vertical fall behavior.
2. `update_player_interactions()` is still too broad for tick-accuracy work and
   should become an ordered ASM-backed subdispatcher.
3. The hard-death restart helper `0x520:0x011A` still controls unknown persistence
   and game-over behavior.
4. Projectile object/state and impact-redraw policy still need a complete table.
5. Level-0 entrance mapping and completion/progression flags remain prototype
   behavior despite the improved movement/collision model.

## Runtime behavior changed?

No gameplay logic was intentionally changed in this pass.  This is an accuracy
infrastructure pass: it makes the current state auditable and gives future passes
a precise place to record whether a behavior is exact, partial, heuristic, or
known wrong.
