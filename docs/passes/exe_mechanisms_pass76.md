# Pass 76 — Accuracy/status registry cleanup

This pass intentionally does **not** change gameplay behavior.

The goal is to make the project easier to continue without mixing up:

- behavior that is confirmed from ASM,
- behavior that is only partially confirmed,
- asset/data mappings that are confirmed but whose runtime logic is not complete,
- heuristics,
- known wrong behavior,
- unimplemented/prototype systems.

## Added files

```text
docs/ACCURACY_STATUS.md
docs/ASM_EVIDENCE_INDEX.md
docs/registry/mechanics_status.json
tools/audit_mechanics_status.py
```

## New status labels

```text
asm_verified
asm_partial
data_verified
heuristic
known_wrong
unimplemented
```

## Why this matters

Recent testing showed that several systems were implemented from a mix of ASM, visual testing, and guesses.  That makes future changes risky because an implemented mechanic can look authoritative even when it is still a heuristic.

The registry now records the current trust level for each important mechanic.

Examples:

- `landmine_0x4d` is `asm_verified` for the instant death trigger and idle/trigger object split.
- `dynamite_exit_0x74_0x71` is `asm_verified` for the broken-door tile rewrite.
- `enemy_0x24_helmet` is only `asm_partial`, because the independent upper/lower animation still needs final validation.
- `animated_decor_tiles` is `heuristic`, because frame ranges have already been caught wrong during testing.
- `overworld_logic` is `unimplemented` except for early UI/8x8 page identification.

## New audit command

```bash
python tools/audit_mechanics_status.py
```

It validates that every entry has:

- a known status,
- implementation pointers,
- evidence for non-placeholder mechanics,
- known gaps / next actions for incomplete mechanics.

## Validation

```bash
python tools/audit_mechanics_status.py
python tools/audit_project.py
PYTHONDONTWRITEBYTECODE=1 python -m compileall -q openagent openagent.game_assets
```
