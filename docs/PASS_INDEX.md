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

- Pass 90: Rechecked raw `0x77` teleporter cooldown/nudge and normal jump-start headroom gate; fixed destination re-exit ping-pong and blocked jumps into a solid tile above.

- Pass 91: Rechecked damage-gated bank-12 enemies and several missed actor visuals: 0x58 closed-top/vulnerable-open hit policy, 0x6D fire walker, 0x23 satellite score target, 0x40 upper-only animation, and 0x4D triggered-mine explosion draw.
- Pass 92: Rechecked `DS:69F5/DS:69F6` hard-death lifecycle; implemented the signed table-driven upward-then-downward death arc, kept world/actor updates running during death, and reset the mission state after the countdown.
- Pass 93: Re-audited the mission HUD/status routine (`SAM1:0x181F1..0x1849E`); added the two-cell ammo icon, fixed speed/dynamite/key/floppy slots, removed the fake glasses HUD icon, and moved lives to the ASM slot loop.
- Pass 94: Re-audited raw `0x63` / state `0x21`; fixed the player-origin firing gate, moved the ceiling laser spawn to `actor_y+8`, and added the exact narrow `0x53C4` contact helper for known 0x53C4 hazards.
- Pass 95: Re-audited the projectile helper path for raw `0x63`: object `0x00C7` is rewritten to object `0x72/state 0x89`. Pass 96 corrects the damage-policy interpretation.

- Pass 96: Re-opened object-`0x72` projectile states; corrected state `0x89` to narrow generic `0x53C4` hurt, moved direct hard-death policy to object `0x72/state 0x25`, and made object-`0x72` solid impacts invisible instead of drawing the generic wall spark.
- Pass 97: Rechecked object-`0x72` laser overlap against `SAM1:0xA660..0xA6F0`; narrow laser states now compare against the player's 10x16 origin rectangle instead of the full decoded sprite footprint.
