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
- Status: `asm_partial`
- Evidence: pass 58-61, pass 70
- Current gaps: exact field slots and all icon conditions.

### Player death lifecycle
- State fields: `DS:69F5`, `DS:69F6`, lives `DS:6A40`
- Status: `asm_partial`
- Evidence: pass 55, pass 57, pass 62, pass 63
- Current gaps: exact animation sequence, freeze/respawn transition, and level reset semantics.

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
- State: `0x21`
- Status: `asm_partial`
- Evidence: earlier 0x63 notes; needs consolidation
- Current gaps: this was corrected several times and needs a fresh single-source audit note.

### Projectiles
- Status: `asm_partial`
- Evidence: pass 64
- Current gaps: complete projectile object/state table and exact impact-spark policy.

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
