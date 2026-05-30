# Next Research Queue

Highest-value unknowns after pass 70.

## UI / overworld / tables

1. Decode the table/window drawing routines around the 8x8 sprite pages:
   - `DS:6E36` menu/table page 0
   - `DS:6E3A` menu/table page 1
   - `DS:6E32` HUD/status page
2. Identify the original menu/title/status strings and their control codes.
3. Map overworld entrance handling, completion flags, and popup/table dialogs.
4. Replace prototype overworld labels with the real table/popup renderer.

## Player lifecycle

1. Verify full player death state after `DS:69F5 = 1`, `DS:69F6 = 0x23`:
   - animation cels,
   - sound,
   - respawn timing,
   - life decrement,
   - level reset vs same-level continuation.
2. Audit generic hurt vs hard death callers and write a single damage policy module.

## Projectiles and enemy hit behavior

1. Separate player bullet, enemy bullet, laser, lightning, and shrapnel actor states.
2. Verify when projectile impact spark is visible and when the projectile slot is just consumed.
3. Confirm per-enemy HP/timer fields where `DS:34DC` is overloaded as both HP-like state and countdown.

## Remaining gameplay mechanics

1. Overworld progression and per-level completion.
2. Door/key variants beyond the dynamite exit.
3. Moving platforms and hidden platforms against exact runtime collision writes.
4. Animated decorative tiles that still use heuristic frame ranges.

## Build hygiene

1. Keep temporary PNGs out of the root.
2. Run `tools/audit_project.py` and `python -m compileall openagent secret_agent_editor` before every handoff.
3. Avoid adding more logic to `runtime.py` unless it is a small integration call into a focused module.

## Cleanup queue after pass 73

1. Extract map pickup/interaction dispatcher into a dedicated module.
2. Split draw/render entity helpers out of `runtime.py`.
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
- `enemy_0x63_ceiling_laser`
- `player_death_lifecycle`
- `projectile_policy`
- `overworld_logic`


## Dedicated overworld ASM audit

Level 0 now has its own module (`openagent/overworld.py`) and research note
(`docs/OVERWORLD_RESEARCH.md`).  The highest-value next ASM task is to replace
heuristic `WORLD_BLOCKED_CODES` with the original island-map tile test, then
trace entrance marker handling and completion flags.

### Pass 78 immediate overworld next step

Before changing world-map movement, run:

```bash
python tools/audit_overworld_data.py
```

Then trace the EXE branch that reads player input while level `0` is active and
compare every collision decision against the raw code positions in
`docs/registry/overworld_level0_inventory.json`.
