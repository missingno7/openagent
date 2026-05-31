# ASM Evidence Index

This is the human-readable companion to `docs/registry/mechanics_status.json`.
It is intentionally concise: use it to find the current source of truth quickly.


## Tick-accuracy entry points

Use these when the question is not "what does this mechanic do?" but "does the Python tick happen in the same order as the EXE?"

- Human map: `docs/TICK_ACCURACY_LEDGER.md`
- Machine map: `docs/registry/tick_accuracy_ledger.json`
- Annotated ASM working copy: `dissassembly/annotated/SAM1_tick_accuracy_excerpts.asm`
- Audit: `python tools/audit_tick_accuracy.py`

Current phase rows cover mission fixed tick order, hard-death arc, normal mission motion, raw `0xA7` barrel interaction, overworld level-0 tick, animated decor/contact policy, and projectile/enemy contact policy. Pass 118 tightens the raw-`0xA7` player/barrel contact rectangle from full-sprite overlap to the ASM `x+3..x+12`, `y..y+15` interval test. Pass 119 adds raw `0x51/0x52` stationary launcher cadence/origin; pass 120 corrects their movement/body helper policy back to non-solid/non-contact and documents the Python render-anchor compensation for projectile Y; pass 121 closes the remaining broad `check_enemy_touch()` fallback path.

## High confidence / mostly verified

### Laser field + computer
- Raw: `0x82`, `0x83`, `0x84`
- Runtime visuals: `0x025B`, `0x025C`, `0x025D`
- Status: `asm_verified`
- Evidence: pass 41, pass 55
- Current gaps: exact laser blink phase still worth visual comparison.

### Landmine
- Raw: `0x4D`
- Objects/states: `0x0270`, `0x0271/state 0x17`
- Status: `asm_verified`
- Evidence: pass 53, pass 54, pass 63, pass 113
- Important point: touching idle `0x0270` immediately starts player hard death; the later explosion frame is not the primary death trigger. Pass 113 confirms the triggered `0x0271/state 0x17` blast uses direct draw/clear helper calls, not persistent extra explosion actors.

### Dynamite + exit door
- Raw: `0x74`, `0x71`
- Objects: `0x027B`, `0x0279`, `0x027A`, `0x027D`, `0x027E`
- Status: `asm_verified`
- Evidence: pass 66, pass 67, pass 68
- Important point: the door does not disappear; both upper and lower broken/passable tiles remain.

## Medium confidence / partially verified

### HUD/status bar
- Assets: `SAM?02.GFX`, 8x8 EGA sprites
- Pointers: `DS:6E32` HUD page, `DS:6E36/DS:6E3A` table/menu pages
- Routine: `SAM1:0x181F1..0x1849E`
- Status: `asm_partial` for the broad UI entry; mission HUD slots are now traced
- Evidence: pass 58-61, pass 70, pass 93
- Confirmed: score slots `0x00..0x05`, ammo icon slots `0x0C..0x0D`, ammo digits `0x0E..0x0F`, speed `0x14`, dynamite `0x19`, red/blue/green keys `0x1B..0x1D`, floppy `0x1E`, lives starting at slot `0x21`.
- Current gaps: menu/table windows and special text control codes.

### Player death lifecycle
- State fields: `DS:69F5`, `DS:69F6`, lives `DS:6A40`
- Status: `asm_partial`
- Evidence: pass 55, pass 57, pass 62, pass 63, pass 92, pass 105
- Confirmed: `DS:69F6=0x23` drives a signed table arc through `SAM1:0x1A61..0x1AE8`; positive entries throw the player upward, negative entries make him fall, Y is clamped to `0x10..DS:683A+0xB8`, world/actor updates should not freeze, and pass 106 corrects the platform detail: actor updates continue after the death branch, and moving-platform carry has no `DS:69F5` guard, so it can catch the death sprite.
- Current gaps: exact `0x520:0x011A` restart helper semantics for score/ammo/inventory persistence and game-over/menu flow.

### Normal mission player movement
- Fields: `DS:681E`, `DS:34AF`, `DS:34EA`, `DS:6EC1`
- Status: `asm_partial`
- Evidence: pass 9, pass 12, pass 80-84
- Confirmed: normal horizontal ramp, normal jump/fall shared table, apex transition tick, atomic falling, exact static `+0x1CC/+0x1CD` fall probes, and dynamic-platform crossing landing.
- Current gaps: original dynamic-platform actor overlap branch, raw-`0xA7` `0x1389` state/timer side effects and blocked-push release, actor-backed solid fall overlap, ladders/direct vertical movement, difficulty modifiers.

### Enemy `0x24`
- Object/state: `0x0065/state 0x27`
- Fields: `DS:34DC`, `DS:34DE`, `DS:34D8`, `DS:34DA`
- Status: `asm_partial`
- Evidence: pass 46-49, pass 54
- Current gaps: exact independent upper/lower animation and projectile origin validation.

### Enemy `0x63`
- Raw/object/state: raw `0x63`, object `0x0345`, state `0x21`; emitted projectile object `0x00C7` becomes `0x72/state 0x89`.
- Status: `asm_partial`, but the core state-`0x21` firing/contact path is now consolidated.
- Evidence: pass 41, pass 94, pass 95, pass 96, pass 97.
- Confirmed: timer `DS:34DA` arms against `DS:34D8`; failed player-under-column gate decrements back to armed-minus-one; gate is strict `actor_x-16 < DS:34EE < actor_x+16` and `actor_y < DS:34F0`; projectile helper gets `actor_y+8`; body contact calls helper `0x53C4`; emitted object `0x00C7` is rewritten by helper `0x5784` to object `0x72/state 0x89`, whose 10x16 rectangle also routes through generic `0x53C4` hurt and uses the same player-origin 10x16 rectangle (`DS:34EE..+9`, `DS:34F0..+15`) confirmed for object-`0x72` in pass 97.
- Current gaps: candidate-position ceiling-track byte probes and state-`0x89` map-collision/redraw side effects still need a focused reference test.

### Projectiles
- Status: `asm_partial`
- Evidence: pass 64, pass 95, pass 96, pass 97
- Confirmed: helper `0x5784` maps player/ordinary shots to state `0x07`; object `0x72` normally maps to state `0x25`, while ceiling-laser input object `0x00C7` is rewritten to object `0x72/state 0x89`; dispatcher order shows state `0x89` calls generic `0x53C4`, while state `0x25` owns the direct hard-death rectangle. Both narrow laser policies use the player's origin gameplay rectangle (`DS:34EE..+9`, `DS:34F0..+15`), not the full decoded sprite.
- Current gaps: complete projectile object/state table, exact object-`0x72` foreground redraw policy, and exact impact-spark policy for non-laser projectiles.

### Stationary launchers `0x51/0x52`
- Raw/object/state: raw `0x52` -> object `0x01D0/state 0x0A` right-facing; raw `0x51` -> object `0x01D1/state 0x0B` left-facing.
- Status: `asm_partial`, with firing cadence/origin now traced.
- Evidence: pass 26, pass 119, pass 120, pass 121.
- Confirmed: `SAM1:0x6B88/0x6C73` increments `DS:34DA` before the player row/front gate; the timer resets only after a successful helper `0x5784` spawn. The row gate compares `(player_y+8)&0xfff0` to `actor_y&0xfff0`. Raw `0x52` fires object `0x01D6` from `actor_x+8, actor_y`, direction `+1`, speed `4`; raw `0x51` fires from `actor_x-8, actor_y`, direction `-1`, speed `4`.
- Confirmed negative policy: decoded shot-damage evidence from pass 29 does not include objects `0x01D0/0x01D1`; pass 120 removes the unsupported movement/body helper reconstruction that made them solid/contact-harmful; pass 121 also excludes them from the broad `check_enemy_touch()` fallback. They are hostile through emitted projectile `0x01D6`, not through body contact.
- Python note: helper `0x5784` receives `actor_y`, while the runtime stores `Projectile.y = actor_y + 7` because ordinary horizontal projectile sprites render at `y-7`; the visible top therefore lines up with the ASM helper Y.
- Current gaps: exact body-contact dispatcher absence for the related raw `0x3C/0x3D` launcher pair is still not separately audited.


## Low confidence / should audit next

### Animated decorations
- Raw examples: `0x40`, `0x78`, `0xD4`
- Status: `asm_partial`
- Evidence: pass 43, pass 53, pass 54, pass 91, pass 115
- Confirmed: raw `0x40` / object `0x0131` / state `0x2B` only advances `DS:34D8/34D6` in `SAM1:0xB599..0xB5FC` and does not call player-contact helper `0x53C4`; its lower cel is the bank9:1 part of the two-cell composite.  State `0x2C` only routes player contact through the explicit object-`0x0103` helper call.
- Current gaps: object-family frame sources should be generated from renderer ranges rather than hand-coded bank/tile refs.

### Overworld and table popups
- Status: `asm_partial` / `data_verified` split
- Evidence: pass 70 identifies UI pages; pass 77 isolates overworld logic and records level-0 data facts; pass 98 traces the top-down movement/collision path; pass 99 splits level-0 `CS:0x2E20` collision parsing from mission parsing; pass 100 reconstructs the world-map scroll registers and direction-processing order; pass 101 aligns player draw/animation and implements automatic house entry/completion cels; pass 102 skips the static 0x59 marker, keeps checked houses re-enterable via origin-based entry/release, and fixes full death reset.
- Data facts: level 0 is the island map; raw `0x59` is the single player marker; `0x4D/0x4E/0x4F/0x50` form 16 entrance anchors per episode, with adjacent `0x4D/0x4E` counted as one wide building.
- Confirmed: when `DS:681C == 1`, movement uses the `SAM1:0xBAF5..0xBC0A` top-down branch; it processes direction flags right, left, down, up, checks the attempted offset before writing position, and mutates `DS:6838/683A` with fixed margins instead of using a centered camera. Collision helper `SAM1:0xB7D9..0xB8B0` samples runtime body byte `+0x1CC` at player-origin rectangle `x+3/x+12`, `y/y+15`, ignoring `+0x1CD`. Level 0 builds those bytes from the `CS:0x2E20` world parser, not the mission parser; raw `0x55` and `0x61` are body-solid there, while `0x30` is body-clear. The level-0 draw path uses DS:34EE/34F0 directly with DS:3500/34F6 player animation state, raw 0x59 is suppressed from static rendering, completed house cels use the neighbouring bank-1 16..19 family, and checked houses remain active entrances after the player origin leaves and re-enters the footprint.
- Current gaps: exact entrance-to-level mapping, original windows/popups, persistent completion/progression flags, and coordinate-specific DOSBox comparison for any remaining choke points.

## Rule for future passes

Every future pass should either:

1. upgrade an entry by adding evidence,
2. downgrade an entry when user testing shows a mismatch,
3. split a broad entry into smaller exact entries, or
4. add a new entry for a newly discovered mechanic.

## Overworld level-0 data audit

- Status: `data_verified` for raw marker inventory; `asm_partial` for movement/collision/camera/draw/entry after pass 102.
- Evidence: `tools/audit_overworld_data.py`, `docs/registry/overworld_level0_inventory.json`, pass 78, pass 98, pass 99, pass 100, pass 101, pass 102.
- Confirmed raw facts: one `0x59` player marker per episode and sixteen entrance anchors per episode; `0x4D/0x4E` is one wide building footprint, `0x4F/0x50` are single-cell markers.
- Confirmed ASM behavior: top-down movement uses runtime `+0x1CC` body-byte probes, level 0 uses its own `CS:0x2E20` map-token table to populate those bytes, world scrolling follows the reconstructed `DS:6838/683A` threshold/clamp logic, player draw/turning uses the DS:3500/34F6 animation family at the same origin used by collision, raw 0x59 is treated as a marker only, and completed houses remain enterable after origin-based release.
- Not yet ASM evidence: entrance-to-level mapping, completed-level flags, popup/table behavior, coordinate-specific verification for any remaining map choke points.
