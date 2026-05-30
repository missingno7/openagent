# Pass 78 - Overworld research guardrails and reproducible data audit

Scope: no gameplay behavior changes.  This pass makes the level-0/island-map
research repeatable before replacing the current heuristic overworld movement
with ASM-derived logic.

## Added tooling

- `tools/audit_overworld_data.py`
  - Loads the real `SAM?03.GFX` level data through the existing project loader.
  - Inspects level `0` for each episode.
  - Emits player marker positions, entrance marker positions, and high-frequency
    raw codes.
  - Supports `--json` so the report can be checked into docs/registry.

- `docs/registry/overworld_level0_inventory.json`
  - Generated data snapshot from the tool.
  - This is data evidence only, not ASM evidence.

## Confirmed/reproducible data facts

The data audit confirms the earlier manual notes:

| Episode | raw `0x59` player marker | entrance count from `0x4D/0x4F/0x50` |
| --- | --- | --- |
| 1 | `(4,2)` | 16 |
| 2 | `(4,4)` | 16 |
| 3 | `(36,6)` | 16 |

The tool also prints the row-major prototype ordering currently used by
`openagent/overworld.py`.  That order is still marked heuristic until the EXE
entrance-selection routine is traced.

## ASM status

This pass deliberately does **not** promote overworld behavior to ASM-verified.
The current state remains:

- raw marker inventory: `data_verified`
- movement/collision: `heuristic`
- entrance-to-level mapping: `heuristic`
- completion flags and table popup behavior: `unimplemented/heuristic`

## Why this helps next

The next ASM pass can now compare the executable's world-map collision and
entrance code against a stable raw-data report instead of relying on memory or
visual guesses.
