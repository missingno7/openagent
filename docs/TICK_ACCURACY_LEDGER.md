# Tick Accuracy Ledger

This is the working map for turning the Python runtime into a tick-accurate
representation of the original Secret Agent executable.

The older documents are still useful, but they answer different questions:

- `docs/passes/` records chronological research history.
- `docs/MECHANICS_INDEX.md` summarizes implemented gameplay features.
- `docs/ASM_EVIDENCE_INDEX.md` points to the strongest human-readable evidence.
- `docs/registry/mechanics_status.json` tracks mechanic confidence.
- `docs/registry/tick_accuracy_ledger.json` is the machine-readable tick map.
- `dissassembly/annotated/SAM1_tick_accuracy_excerpts.asm` is the first ASM file
  with inline comments for the critical tick branches.

Use this file when you need to answer: **what exact part of the Python runtime is
supposed to match which ASM branch, and what is still guessed?**

## Comment tags for ASM and Python

Use these consistently in annotated ASM excerpts and runtime comments:

| Tag | Meaning |
|---|---|
| `FACT` | Directly read from ASM/data or already proven by a regression test. |
| `ASM` | The concrete address/range that supports the claim. |
| `PY` | Python entrypoint that currently implements the behavior. |
| `VERIFIED` | Regression/DOSBox comparison currently backs the behavior. |
| `PARTIAL` | ASM evidence exists, but timing/state/edge cases are incomplete. |
| `HYP` | Hypothesis. Do not treat it as implementation truth. |
| `GAP` | Known blind spot that should drive the next pass. |
| `TODO` | Concrete next action. |
| `WRONG_PREVIOUS_ASSUMPTION` | Useful when a plausible interpretation was disproven. |

## Phase map

| Tick phase | Status | Python entrypoint | ASM anchors | Main gaps |
|---|---|---|---|---|
| Mission fixed tick order | `asm_partial` | `openagent/runtime.py::update_mission_simulation` | `SAM1:0x1A21..0x1B5D`, `SAM1:0x1A61..0x1AE8` | Full post-`0x1B5D` phase table; restart helper `0x520:0x011A`; broad interaction dispatch order. |
| Hard-death arc | `asm_partial` | `openagent/runtime.py::update_player_death_tick`, `openagent/player_lifecycle.py::advance_death_bounce_tick` | `SAM1:0x1A61..0x1AE8`, `DS:69F5`, `DS:69F6`, `DS:683A` | Exact death draw timing; lives-zero/game-over branch; persistence through restart. |
| Normal player motion | `asm_partial` | `openagent/runtime.py::update_player_tick`, `openagent/player_motion.py` table helpers, `openagent/movement_collision.py` motion helpers | `SAM1:0x28ED6..0x28F35`, `SAM1:0xB7D9..0xB8A4`, `SAM1:0xB8B3..0xBA49`, `SAM1:0xBC0E..0xBD8A` | Pass 130 applies BC0E vertical fall/jump before same-tick horizontal B7D9 probing for one-tile openings; pass 131 corrects the unshifted DS:34AF table so counter 1 is 0px and falling can hit modulo-16 doorway alignment; exact outer wrapper order, raw `0x62` actor overlap, actor-backed solid fall overlap, ladders/direct vertical movement and difficulty modifiers remain open. |
| Raw `0xA7` pushable barrel | `asm_partial` | `openagent/movement_collision.py::player_barrel_actor_overlap`, `try_push_barrel`, `move_barrel_vertical`, `release_barrel_against_wall` | `SAM1:0x82E3..0x8742`, `0x81C8..0x8288`, `0x83C4..0x848A`, `0x8542..0x8742` | `x+3..x+12` player/barrel rectangle implemented. Pass 123 corrects pass 122: wall-blocked pushes are **not** the destructive `0x00AA/state 0x1389` score branch; wall release now keeps raw `0xA7/state 0x1388`. Pass 126 fixes the live polling path after body pass-through. Pass 127 removes the unsupported player-gravity coupling: ordinary barrel push and unsupported fall now use a named 4px actor-step reconstruction from actor-speed evidence instead of the player one-pixel substep / `DS:34AF` table. Pass 128 locks pushed-off-edge fall so side contact can block but cannot keep moving the barrel horizontally until it lands. Exact wall-push caller/store and exact pushed-off-edge store remain open. |
| Level-0 overworld tick | `asm_partial` | `openagent/overworld.py::update_overworld_tick` | `SAM1:0xB7D9..0xB8B0`, `SAM1:0xBAF5..0xBC0A`, `CS:0x2E20` | Entrance dispatch mapping; persistent completion flags; popup/table windows; coordinate-specific reference tests. |
| Animated decor/contact policy | `asm_partial` | `openagent/animation.py`, `openagent/entities.py`, `openagent/rendering.py` | `SAM1:0xB599..0xB5FC`, state `0x2B/0x2C` | Generated frame-source tables; raw `0x78` audit; clean split between non-contact decor and hazards. |
| Projectile/enemy contact tick | `asm_partial` | `openagent/combat.py`, `openagent/runtime.py::update_entities_tick`, `openagent/runtime.py::check_enemy_touch`, `openagent/movement_collision.py::player_dynamic_body_collides` | `SAM1:0x53C4`, `SAM1:0x547C`, `SAM1:0x5784`, `SAM1:0x5A37..0x5CD8`, `SAM1:0x5CDB..0x61F8`, `SAM1:0x6B74..0x6D47`, `SAM1:0x9A25..0x9AB2`, `SAM1:0xA2AF..0xA604` | Full projectile object/state table; exact `0x547C` impact side effects; object-`0x72` redraw/map-collision side effects; broad generic body-contact fallback still needs a full allowlist audit. |

The JSON ledger has the full exact claims, blind spots, tests and next actions.
Run this after changing the ledger or adding a tick-accuracy pass:

```bash
python tools/audit_tick_accuracy.py
```

`tools/check_handoff.py` also runs this audit, so stale paths should be caught
before a zip is handed back.

## Current highest-value blind spots

1. **Raw `0xA7` barrel** — vertical falling no longer uses broad side collision,
   and pass 118 replaced broad full-sprite player/barrel contact with the ASM
   `x+3..x+12`, `y..y+15` rectangle.  Pass 123 corrects pass 122: wall-blocked
   pushes are not the destructive `0x00AA/state 0x1389` score branch.  The current
   wall-release reconstruction keeps raw `0xA7` body-pass-through but top-solid;
   pass 125 restores it on the free side from the same ASM shrunken X interval,
   not from a live front-wall probe or full-tile clearance. Pass 126 fixes the runtime polling regression that left the barrel stuck once it became pass-through.  Pass 127 replaces the unsupported player-`DS:34AF` gravity reuse with a named 4px actor-step reconstruction for ordinary barrel push/fall, and pass 128 adds the unsupported-fall side-push lock.  The biggest remaining mismatch risk is the exact wall-push caller/store ASM
   path/DOSBox pixel timing, exact pushed-off-edge state/store timing, helper-`0x547C`
   projectile-hit branch, and whether the individual redraw cleanup calls matter.
2. **Normal player-motion wrapper order/table indexing** — pass 130 fixes the observed one-tile
   opening regression by running the BC0E vertical fall/jump phase before the
   same-tick horizontal B7D9 probe, and pass 131 fixes the DS:34AF off-by-one
   so the jump/fall arc actually reaches modulo-16 doorway alignment. The outer `0x520:0x68F5 / 0x520:0x6A0E`
   wrappers still need a full trace before this can be marked fully verified.
3. **Mission interaction dispatch order** — `update_player_interactions()` still
   mixes pickups, hazards and doors. It should become a small ordered table once
   the ASM caller order is traced.
4. **Restart helper after hard death** — until `0x520:0x011A` is traced, reset
   behavior can accidentally hide differences in lives/ammo/inventory persistence.
5. **Projectile / stationary launcher policy** — object `0x72` state split is
   better now. Pass 119 fixed `0x51/0x52` elapsed firing cadence and helper X/Y
   parameters; pass 120 corrected the unsupported solid/contact-hurt
   reconstruction; pass 121 also fixed the remaining generic `check_enemy_touch()`
   fallback path, so raw `0x51/0x52` are non-solid and harmless on body contact.
   Pass 129 adds the `0x3C/0x3D` rocket pair and confirms the key projectile
   rule: `0x01D6`, `0x01E8`, and `0x01EC` hurt through helper `0x53C4` but
   keep flying through the player; `0x547C` owns impact/consumption.  The
   remaining risk is broader projectile object/state redraw, exact `0x547C`
   side effects, render-anchor consistency across all projectile families, and a
   complete generic body-contact allowlist audit.
6. **Overworld entrance/progression flags** — movement/collision is much closer
   than before, but progression remains prototype-like.

## Workflow for the next passes

1. Pick one row from the phase map, not a random file.
2. Open `docs/registry/tick_accuracy_ledger.json` and copy its `asm_refs`,
   `runtime_entrypoints`, `blind_spots`, and `next_actions` into the pass plan.
3. Add or extend an annotated ASM excerpt under `dissassembly/annotated/`.
4. Change Python only where the ledger says the behavior belongs.
5. Add a small deterministic check under `tools/check_*.py` when possible.
6. Update the ledger and the mechanic registry in the same commit.
7. Run:

```bash
python tools/check_handoff.py
```
