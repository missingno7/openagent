# Pass Log Index

Chronological pass notes live under `docs/passes/`. They are audit history, not the main onboarding path.

Start here for day-to-day work:

- `docs/PROJECT_MAP.md` — current code ownership and safe refactor targets.
- `docs/MECHANICS_INDEX.md` — concise implemented-mechanics status.
- `docs/ASM_EVIDENCE_INDEX.md` — where the important ASM evidence is documented.
- `docs/TICK_ACCURACY_LEDGER.md` — ASM refs -> Python tick entrypoints -> blind spots -> tests.
- `docs/NEXT_RESEARCH_QUEUE.md` — highest-value remaining unknowns.
- `docs/PERFORMANCE_NOTES.md` — render/timing hot-path rules.

## Cleanup / structure milestones

| Pass | Summary |
|---:|---|
| 72 | Extracted HUD/UI rendering and the player dataclass out of `runtime.py`. |
| 73 | Moved shared constants to `openagent/game_constants.py` and player lifecycle to `openagent/player_lifecycle.py`. |
| 74 | Moved projectile/combat/hit-policy helpers to `openagent/combat.py`. |
| 76 | Added mechanics accuracy registry, ASM evidence index, and registry audit tool. |
| 77 | Moved prototype level-0 island-map logic to `openagent/overworld.py`. |
| 107 | Removed obsolete mission fixed-step wrappers, added bytecode-free `tools/check_handoff.py`, and refreshed docs. |
| 108 | Moved render-only interpolation/camera/draw helpers to `openagent/rendering.py` and trimmed runtime imports. |
| 109 | Moved level-image cache rendering, Tk/window controls, and teleporter state into focused mixins. |
| 111 | Moved low-level movement/collision/barrel/platform helpers into `openagent/movement_collision.py`. |
| 112 | Restored the hard-death runtime visual lookup import and added a handoff smoke test for it. |
| 113 | Removed the leftover persistent three-explosion fan-out from triggered raw `0x4D` mines and added a regression test. |
| 114 | Refactored render interpolation into a shared presentation smoother for player, actors and camera. |
| 115 | Re-audited raw `0x40` / object `0x0131` / state `0x2B`: it is decorative/non-contact and its lower cel is bank9:1. |
| 116 | Corrected raw `0xA7` barrel gravity so falling remains vertical and side body cells cannot stop the downward step. |
| 117 | Added the tick-accuracy ledger, annotated ASM excerpts, and a handoff audit tying ASM refs to Python tick entrypoints and blind spots. |
| 118 | Re-audited raw `0xA7` player/barrel contact: implemented the ASM `x+3..x+12`, `y..y+15` rectangle and added a regression test. |
| 119 | Re-audited raw `0x51/0x52` stationary launchers: fixed elapsed firing cadence and helper projectile origin, but pass 120 later corrects the body-policy conclusion. |
| 120 | Corrected raw `0x51/0x52` to non-solid/non-contact bodies, compensated projectile render Y, and removed the unsupported raw-`0xA7` blocked-release horizontal side-pop. |
| 121 | Fixed the remaining global `check_enemy_touch()` fallback so stationary launchers cannot hurt by touch, and documented raw-`0xA7` release/fall as still partial instead of overclaiming it. |

## Recent ASM / gameplay passes

| Pass | Summary |
|---:|---|
| 92 | Implemented `DS:69F5/69F6` hard-death signed table arc and mission reset after countdown. |
| 93 | Re-audited mission HUD/status routine; fixed ammo icon, speed/dynamite/key/floppy/lives slots. |
| 94 | Re-audited raw `0x63` ceiling laser; fixed player-origin firing gate, spawn point, and shared narrow contact helper. |
| 95 | Rechecked projectile helper `0x5784`; `0x00C7` maps to object `0x72/state 0x89`; pass 96 corrects policy. |
| 96 | Split object-`0x72` projectile states: state `0x89` narrow generic hurt, state `0x25` direct hard death. |
| 97 | Corrected object-`0x72` laser hit test to player-origin 10x16 rectangle, not full decoded sprite. |
| 98 | Re-audited level-0 movement/collision helper; switched overworld collision to runtime `+0x1CC` body-byte probes. |
| 99 | Added dedicated level-0 world collision table from `CS:0x2E20`. |
| 100 | Reconstructed level-0 movement order and `DS:6838/683A` world camera thresholds/clamps. |
| 101 | Aligned level-0 player draw origin, walking animation, automatic house entry, and checked-house redraw. |
| 102 | Fixed world start marker duplication, checked-house replay gating, and full hard-death level reset. |
| 103 | First interpolation smoothing pass; later superseded by pass 104 for platform jitter. |
| 104 | Simplified interpolation to linear fixed-step alpha and fixed carried-player/platform snapshot phase. |
| 110 | Added optional render smoothing mode while keeping linear interpolation as the accuracy baseline; pass 114 replaces the first curve. |
| 105 | Froze mission camera during hard-death and clamped death fall to `DS:683A+0xB8`; pass 106 supersedes platform detail. |
| 106 | Restored ASM-accurate death/platform ordering: moving platforms can catch/carry the death animation. |
| 113 | Rechecked raw `0x4D` triggered mine state `0x17`; ASM directly draws/clears the surrounding blast and does not spawn extra persistent explosion actors. |
| 115 | Rechecked raw `0x40` state `0x2B`: no `0x53C4` contact helper, lower cel bank9:1, and broad generic contact disabled. |
| 116 | Rechecked the raw `0xA7` barrel fall approximation: gravity now uses only vertical landing probes and no longer reuses broad horizontal/body collision, so pushed-off barrels fall straight down past side solids. |
| 117 | Added a tick-accuracy ledger and annotated ASM excerpts so future changes start from ASM refs, Python entrypoints, blind spots and tests instead of scattered notes. |
| 118 | Re-audited raw `0xA7` player/barrel interaction: broad full-sprite overlap was replaced by the ASM shrunken contact rectangle, while `0x1389` state side effects remain tracked as partial. |
| 119 | Re-audited raw `0x51/0x52` stationary launchers: `DS:34DA` is elapsed time, not a line-of-sight countdown; fixed immediate charged firing and helper `actor_y` projectile origin. |
| 120 | Corrected pass 119 body policy: raw `0x51/0x52` are not solid/contact hazards; Python compensates projectile render Y while preserving ASM helper `actor_y`.  Also removed the reconstructed barrel release side-nudge. |
| 121 | Closed the second `0x51/0x52` contact-damage path in `check_enemy_touch()`: the generic body fallback now excludes stationary launchers, while barrel pushed-off-edge / release state remains explicitly tracked as an unresolved `0x1389` accuracy gap. |

## Full archive

The complete historical archive is still available as individual markdown files under `docs/passes/`, including older extraction/data passes and superseded interpretations. When a newer pass corrects an older one, prefer the newer pass and the current status in `docs/registry/mechanics_status.json`.

Before packaging a handoff build, run:

```bash
python tools/check_handoff.py
```
