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
| Normal player motion | `asm_partial` | `openagent/player_motion.py::update_player_tick`, `openagent/movement_collision.py` motion helpers | `SAM1:0xB7D9..0xB8A4`, `SAM1:0xB8B3..0xBA49`, `SAM1:0xBCED..0xBD80` | Raw `0x62` actor overlap; actor-backed solid fall overlap; ladders/direct vertical movement; difficulty modifiers. |
| Raw `0xA7` pushable barrel | `asm_partial` | `openagent/movement_collision.py::player_barrel_actor_overlap`, `try_push_barrel`, `move_barrel_vertical`, `release_barrel_against_wall` | `SAM1:0x82E3..0x8742`, `0x83C4..0x848A`, `0x8542..0x8742` | `x+3..x+12` player/barrel rectangle now implemented; exact `0x1389` actor state, score/sound side effects, and blocked-push release semantics still partial. |
| Level-0 overworld tick | `asm_partial` | `openagent/overworld.py::update_overworld_tick` | `SAM1:0xB7D9..0xB8B0`, `SAM1:0xBAF5..0xBC0A`, `CS:0x2E20` | Entrance dispatch mapping; persistent completion flags; popup/table windows; coordinate-specific reference tests. |
| Animated decor/contact policy | `asm_partial` | `openagent/animation.py`, `openagent/entities.py`, `openagent/rendering.py` | `SAM1:0xB599..0xB5FC`, state `0x2B/0x2C` | Generated frame-source tables; raw `0x78` audit; clean split between non-contact decor and hazards. |
| Projectile/enemy contact tick | `asm_partial` | `openagent/combat.py`, `openagent/runtime.py::update_entities_tick`, `openagent/runtime.py::check_enemy_touch`, `openagent/movement_collision.py::player_dynamic_body_collides` | `SAM1:0x53C4`, `SAM1:0x5784`, `SAM1:0x6B74..0x6D47`, `SAM1:0x9A25..0x9AB2`, `SAM1:0xA2AF..0xA604` | Full projectile object/state table; impact spark policy; object-`0x72` redraw/map-collision side effects; broad generic body-contact fallback still needs a full allowlist audit. |

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
   `x+3..x+12`, `y..y+15` rectangle.  The biggest remaining mismatch risk is
   now the transient `0x1389` state: score/sound/draw cleanup, pushed-off-edge timing, and blocked-push
   release are still reconstructed rather than fully state-modelled.
2. **Mission interaction dispatch order** — `update_player_interactions()` still
   mixes pickups, hazards and doors. It should become a small ordered table once
   the ASM caller order is traced.
3. **Restart helper after hard death** — until `0x520:0x011A` is traced, reset
   behavior can accidentally hide differences in lives/ammo/inventory persistence.
4. **Projectile / stationary launcher policy** — object `0x72` state split is
   better now. Pass 119 fixed `0x51/0x52` elapsed firing cadence and helper X/Y
   parameters; pass 120 corrected the unsupported solid/contact-hurt
   reconstruction; pass 121 also fixed the remaining generic `check_enemy_touch()`
   fallback path, so raw `0x51/0x52` are non-solid and harmless on body contact.
   The remaining risk is broader projectile object/state redraw, render-anchor
   consistency across all projectile families, and a complete generic body-contact
   allowlist audit.
5. **Overworld entrance/progression flags** — movement/collision is much closer
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
