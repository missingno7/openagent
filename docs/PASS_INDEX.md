# Pass Log Index

Chronological pass notes were moved from the `docs/` root to `docs/passes/` so the root documentation stays readable.

Use the pass logs as audit history. For day-to-day orientation, start with:

- `docs/PROJECT_MAP.md`
- `docs/MECHANICS_INDEX.md`
- `docs/NEXT_RESEARCH_QUEUE.md`
- `docs/exe_mechanisms_summary.md`

The pass files are still kept verbatim under `docs/passes/`.

## Cleanup passes

- `docs/passes/exe_mechanisms_pass72.md` — extracted HUD/UI rendering and player dataclass out of `runtime.py`; no gameplay changes.
- **Pass 73** – cleanup-only refactor: moved shared runtime constants into `openagent/game_constants.py` and player hurt/death/respawn lifecycle into `openagent/player_lifecycle.py`.
- **Pass 74** – cleanup-only refactor: moved projectile/combat/hit-policy helpers into `openagent/combat.py`.

## Pass 76

- Added the mechanics accuracy/status registry.
- Added `docs/ACCURACY_STATUS.md`, `docs/ASM_EVIDENCE_INDEX.md`, and `docs/registry/mechanics_status.json`.
- Added `tools/audit_mechanics_status.py` to prevent future handoffs from hiding heuristic/unknown behavior.


## Pass 77

- Moved prototype level-0 island-map logic into `openagent/overworld.py`.
- Added `docs/OVERWORLD_RESEARCH.md` with data facts vs heuristics.
- Updated the mechanics registry so overworld behavior is no longer simply hidden as `unimplemented`.

- Pass 78: Overworld research guardrails; added reproducible level-0 raw-data audit tool and `docs/registry/overworld_level0_inventory.json`.
