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
| 86 | Re-audited normal mission movement against `SAM1:0x532D`, `0xB8B3`, and `0xBC0E..0xBD8A`; fixed the accidental always-on speed-bonus horizontal terminal speed, implemented raw `0x4E` speed bonus timing/HUD icon, and documented why diagonal falling can visually look like ~6 px/tick even though the ASM uses integer 4/8 px terminal steps. |

| 87 | Fixed visible rendering for mine/water animation: `0x4D` now uses `state17_landmine_tile()` in `draw_entities()`, and `0x60` is skipped from cached layers so the live `0x01F3` overlay is not hidden by static foreground. |
- Pass 88: Re-audited raw `0x77` teleporter alignment/rearm and live bank10 idle/warp animation.

- Pass 89: Re-audited raw `0x58` / object `0x0331` / state `0x1F`; fixed bank12 composite top/bottom frame ranges and added its walk/stop/open `DA/DC/DE` timer cycle.
