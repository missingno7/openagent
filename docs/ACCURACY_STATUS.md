# Accuracy Status System

The goal is to stop treating all implemented behavior as equally trustworthy.
Every mechanic should have an explicit status before we build more logic on top of it.

## Status labels

| Status | Meaning | How to use it |
|---|---|---|
| `asm_verified` | The main behavior is backed by a concrete ASM branch/address and runtime code intentionally matches it. | Use for things like the exit-door broken tile rewrite when the exact object IDs and collision writes are known. |
| `asm_partial` | We have ASM evidence for part of the behavior, but some timing, visuals, transitions, or edge cases remain approximate. | This is the default for most reverse-engineered mechanics. |
| `data_verified` | The asset or data mapping is confirmed, but the runtime behavior is not fully traced. | Good for graphics/HUD asset formats before draw logic is complete. |
| `heuristic` | Implemented from visual behavior or inference, not yet proven from ASM/game data. | Treat as suspect. These should be high-priority audit targets. |
| `known_wrong` | We know it differs from the original game. | Should appear in the research queue until fixed. |
| `unimplemented` | Placeholder/prototype only. | Do not depend on it for other mechanics. |

## Registry

The machine-readable registry is:

```text

docs/registry/mechanics_status.json
```

Each entry records:

- mechanic ID,
- raw tile/object/state IDs,
- current implementation files,
- status/confidence,
- evidence docs and ASM refs,
- known gaps,
- next actions.

Run:

```bash
python tools/audit_mechanics_status.py
```

This validates that every entry has a known status, evidence, implementation pointers, and follow-up actions where needed.

## How to use this while working

Before changing a mechanic, check its registry entry:

1. If it is `asm_verified`, avoid changing behavior without adding stronger evidence.
2. If it is `asm_partial`, update only the specific missing part and add the ASM ref.
3. If it is `heuristic`, either verify it from ASM/data or mark exactly what is still guessed.
4. If user testing finds a mismatch, downgrade the entry to `known_wrong` or `asm_partial` and add the symptom.

This should make it clear what is solid, what is a useful approximation, and what still needs real reverse engineering.
