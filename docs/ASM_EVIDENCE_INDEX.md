# ASM Evidence Index

This is the human-readable companion to `docs/registry/mechanics_status.json`.
It is intentionally concise: use it to find the current source of truth quickly.

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
- Evidence: pass 53, pass 54, pass 63
- Important point: touching idle `0x0270` immediately starts player hard death; the later explosion frame is not the primary death trigger.

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
- Evidence: pass 55, pass 57, pass 62, pass 63, pass 92
- Confirmed: `DS:69F6=0x23` drives a signed table arc through `SAM1:0x1A61..0x1AE8`; positive entries throw the player upward, negative entries make him fall, and world/actor updates should not freeze.
- Current gaps: exact `0x520:0x011A` restart helper semantics for score/ammo/inventory persistence and game-over/menu flow.

### Normal mission player movement
- Fields: `DS:681E`, `DS:34AF`, `DS:34EA`, `DS:6EC1`
- Status: `asm_partial`
- Evidence: pass 9, pass 12, pass 80-84
- Confirmed: normal horizontal ramp, normal jump/fall shared table, apex transition tick, atomic falling, exact static `+0x1CC/+0x1CD` fall probes, and dynamic-platform crossing landing.
- Current gaps: original dynamic-platform actor overlap branch, raw-`0xA7` barrel overlap fallback, actor-backed solid fall overlap, ladders/direct vertical movement, difficulty modifiers.

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

## Low confidence / should audit next

### Animated decorations
- Raw examples: `0x40`, `0x78`, `0xD4`
- Status: `heuristic`
- Evidence: pass 43, pass 53, pass 54
- Current gaps: frame counts and frame sources should be data-driven, not guessed.

### Overworld and table popups
- Status: `heuristic` / `data_verified` split
- Evidence: pass 70 identifies UI pages; pass 77 isolates overworld logic and records level-0 data facts.
- Data facts: level 0 is the island map; raw `0x59` is the single player marker; `0x4D/0x4F/0x50` total exactly 16 entrance candidates per episode.
- Current gaps: collision table, entrance-to-level mapping, completion flags, original windows/popups.

## Rule for future passes

Every future pass should either:

1. upgrade an entry by adding evidence,
2. downgrade an entry when user testing shows a mismatch,
3. split a broad entry into smaller exact entries, or
4. add a new entry for a newly discovered mechanic.

## Overworld level-0 data audit

- Status: `data_verified` for raw marker inventory only; gameplay remains `heuristic`.
- Evidence: `tools/audit_overworld_data.py`, `docs/registry/overworld_level0_inventory.json`, pass 78.
- Confirmed raw facts: one `0x59` player marker per episode and sixteen `0x4D/0x4F/0x50` entrance markers per episode.
- Not yet ASM evidence: movement collision, entrance-to-level mapping, completed-level flags, popup/table behavior.
