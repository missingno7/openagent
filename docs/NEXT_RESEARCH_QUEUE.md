# Next Research Queue

Highest-value unknowns after pass 106.

## UI / overworld / tables

1. Decode the table/window drawing routines around the 8x8 sprite pages:
   - `DS:6E36` menu/table page 0
   - `DS:6E3A` menu/table page 1
   - the `DS:6E32` mission HUD slot map is already covered by pass 93
2. Identify the original menu/title strings and their control codes.
3. Trace the exact overworld entrance-to-level mapping and persistent completion/progression flags; runtime now has automatic origin-based entry, checked-house redraw, and re-entry after completion, but the dispatch table is still row-major.
4. Compare the pass-102 movement/collision/draw/entry model against DOSBox reference paths at any remaining problematic coordinates.
5. Replace prototype overworld labels with the real table/popup renderer.

## Player lifecycle

1. Trace the exact restart helper called when `DS:69F6` reaches zero (`0x520:0x011A`):
   - which score/ammo/inventory fields persist,
   - exact game-over/menu branch when lives reaches zero,
   - whether any per-level completion/checkpoint state survives.
2. Capture a DOSBox reference for the two-cel death draw timing and compare it
   with the current bank-13 tile selection, especially at the `DS:683A+0xB8` bottom clamp.
3. Audit generic hurt vs hard death callers and write a single damage policy module.
4. Recheck transient `DS:6EC1` meanings in the moving-platform catch branch; pass 106 models the missing `DS:69F5` behavior, but not every edge of jump/carry state.

## Projectiles and enemy hit behavior

1. Finish the projectile object/state table: player bullet, enemy bullet, lightning, shrapnel, and non-laser object families; passes 96-97 now separate object-`0x72/state 0x25` from `0x00C7 -> 0x72/state 0x89` and confirm their shared player-origin 10x16 hit rectangle.
2. Verify when projectile impact spark is visible and when the projectile slot is just consumed.
3. Confirm per-enemy HP/timer fields where `DS:34DC` is overloaded as both HP-like state and countdown.
4. Rebuild object-`0x72` map-collision foreground redraw side effects around `SAM1:0xA2AF..0xA604` / `0xA4CB..0xA604`; hit rectangle policy is now handled by pass 97.

## Remaining gameplay mechanics

1. Exact overworld entrance dispatch/progression flags beyond the runtime-local checked-house redraw.
2. Door/key variants beyond the dynamite exit.
3. Moving platforms and hidden platforms against exact runtime collision writes.
4. Animated decorative tiles that still use heuristic frame ranges.

## Build hygiene

1. Keep temporary PNGs out of the root.
2. Run `python -m compileall -q openagent tools`, remove generated `__pycache__/`, then run `tools/audit_project.py` before every handoff.
3. Avoid adding more logic to `runtime.py` unless it is a small integration call into a focused module.

## Cleanup queue after pass 73

1. Extract map pickup/interaction dispatcher into a dedicated module.
2. Split draw/render entity helpers out of `runtime.py`; keep `docs/PERFORMANCE_NOTES.md` updated when touching zoom/render hot paths.
3. Turn enemy state branches into named state helpers with ASM references.
4. Continue moving projectile ASM refinements into `openagent/combat.py`.

## Accuracy workflow after pass 76

Before adding more behavior, pick one `asm_partial` or `heuristic` entry from `docs/registry/mechanics_status.json` and either:

1. upgrade it with concrete ASM/data evidence,
2. split it into smaller exact entries,
3. mark the known mismatch precisely, or
4. move remaining guesses into `known_gaps`.

Highest priority suspects:

- `animated_decor_tiles`
- `enemy_0x63_ceiling_laser` — core state path consolidated in passes 94-96; remaining work is ceiling-track probe and state-0x89 impact/map-redraw reference test.
- `player_death_lifecycle`
- `projectile_policy` — hit rectangle split improved in pass 97; remaining work is object/state table + impact/redraw side effects.
- `overworld_logic`


## Dedicated overworld ASM audit

Level 0 now has its own module (`openagent/overworld.py`) and research note
(`docs/OVERWORLD_RESEARCH.md`).  Pass 98 replaced the broad visual collision
heuristic with the original top-down `+0x1CC` body-byte helper.  The next useful
ASM tasks are now entrance marker handling, completion flags, original popup
windows, a DOSBox movement reference capture for any remaining troublesome coordinates, and exact entrance/menu behavior.
