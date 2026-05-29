# EXE Mechanism Pass Summary

This document condenses `docs/exe_mechanisms_pass*.md` and related collision
passes.  The individual pass files are raw research logs; this file says which
conclusion survived cleanup.

## Collision Passes

| Source | Current conclusion |
| --- | --- |
| `exe_collision_table_research.md` | Superseded first extraction.  Useful historical evidence, but it only covered the first token table and misled `0x70`. |
| `runtime_collision_table_research.md` | Extracted all setter call groups.  Current mission maps use `CS:3a59..3a8f` and `CS:66f9..68a7`; exclude `CS:2e20..2e86`. |
| `exe_runtime_mechanisms_pass2.md` | Correct setter branch model: full cell writes when marker arg is zero, overlay-only `+0x1CA` writes when nonzero.  Its original row-major formula is superseded by pass 5. |
| `exe_mechanisms_pass5.md` | Authoritative axis correction: runtime buffer uses X-column stride `0xC8`; `0xD2` has one-way foot cells on the upper row. |

Current rule: build mission collision by replaying `openagent/exe_runtime_collision.py`
relative writes into a runtime grid.  Do not infer it from rendered sprites.

## Player Passes

| Pass | Surviving result |
| --- | --- |
| 3 | Player globals are separate from actor slots; actor slots are 0x20 bytes; control flags and initial jump table access were identified. |
| 4 | Player animation state is driven by `DS:3500`; actor walking animation uses slot fields, not free-running visual cycling. |
| 8 | Replaced continuous jump/gravity assumptions with fixed tick motion and hidden-platform/glasses distinction. |
| 9 | Timing, collision snap and bank 13 frame mapping were refined. |
| 10 | Recovered first explicit jump/fall tables, but pass 12 corrected the model. |
| 11 | Grounding/jump/shooting gates were refined. |
| 12 | Current vertical-motion model: jump and fall share `DS:34AF` byte table; `DS:6EC1` plus `DS:34EA` controls the phase.  Shooting frames corrected to bank 13 tiles 10/11. |

Current rule: player movement is fixed-DOS-tick and table driven.  Avoid adding
new continuous physics constants unless they are explicitly marked as prototype
fallbacks.

## Pickup And Interaction Passes

| Pass | Surviving result |
| --- | --- |
| 13 | Score pickups are dispatched by runtime cell `+0x1CA`; score accumulator is `DS:699A/699C`; score popups use one-based bank 10 tiles. |
| 17 | Bank-14 grave/RIP score corrected: shooting is 500, collecting is 1000. |

Current rule: invert `+0x1CA` runtime visual/object ids through the generated
runtime table before assigning raw-code pickup behavior.

## Actor And Enemy Passes

| Pass | Surviving result |
| --- | --- |
| 3 | Actor records are 0x20-byte structs.  `34E0` is object id, `34E6` is per-tick step, `34E8` is behavior state. |
| 4 | Walking actors flip direction on `+0x1CC` side collision and keep frame ranges in `34D6`. |
| 17 | Actor speed is per DOS tick.  Moving platform `0x62` starts left; later pass 24 adjusts its runtime speed fallback. |
| 18 | Special actor table at `CS:3A59` gives object id, state, speed and timers for bank-14 guards and many special actors. |
| 21 | Raw `0x3F` and `0x41` are retracting spike actors, not static/animated background tiles. |
| 22 | Spike draw origin corrected; raw `0x23`, `0x6E`, and `0x7F` promoted to runtime actors. |
| 23 | Satellite animation research preserved more table entries; pass 24 corrected cadence. |
| 24 | Satellite uses 3 DOS ticks per frame.  Platform `0x62` runtime fallback moves 2 px/tick.  Multi-tile actors `0xAE`, `0x24`, `0x56`, `0x58`, `0x63` promoted. |
| 25 | Projectile helper `0x5784` decoded; normal bullets are object `0x27`, state `0x07`, speed 4 px/tick, bank 1 tiles 38/39.  Guard firing gate is same-row/in-front, not wall raycast. |
| 26 | Stationary shooter traps `0x52`, `0x51`, `0x3C`, `0x3D` are runtime actors with timers and projectile helper calls. |
| 27 | Timed bank-3 beam traps `0x3B/0x3E` are actor states `0x0F/0x10`, not static scenery. |
| 28 | Active gameplay viewport remains fixed 320x200; resized render viewport must not activate off-screen traps early. |
| 29 | Bullet impact sprite corrected to bank 5 tiles 24..27.  Not every actor is damageable; hit logic branches by object id. |
| 30 | Raw `0x63` is a ceiling laser crawler; raw `0xA7` is dynamic pushable barrel. |
| 31 | Ceiling laser firing gate, barrel blocked-push behavior, beam core visuals and shark swimmer were refined. |
| 32 | Shark direction uses bank 4's built-in left/right frames; barrel anti-stick behavior is backed by a dedicated actor overlap path. |
| 33 | Runtime draw order corrected: the EXE draws the player before actor slots, so dynamic actors render over the player. |

Current rule: any raw byte present in the special actor table should be treated
as a candidate runtime actor first.  Bake it into static background only after
proving the EXE does not allocate/update an actor slot for it.

## Rendering And Animation Passes

| Pass | Surviving result |
| --- | --- |
| 6 | Initial player/walker animation mapping.  Later passes corrected several frame choices. |
| 7 | Player walk counter and floor jitter cleanup. |
| 19 | Superseded: it treated background groups as animated. |
| 20 | Correction: `0x35..0x37` are static background variants.  Real animated tile found: raw `0x60` / visual `0x01F3` / bank 4 tile 48 toggles with bank 4 tile 0. |
| 23 | Animation timing for raw `0x60` currently uses a 4-DOS-tick fallback until the exact `DS:6840` schedule is mapped. |
| 33 | Normal/full static runtime cell words draw in `+0x1C6`, `+0x1C8`, `+0x1CA` order before the player; these words are layer order inside the cell, not by themselves player occlusion flags. |
| 34 | Partially superseded by pass 35: `*` rows use the setter's nonzero-marker branch at `0x1059E`, write only the `+0x1CA` overlay word, and do not write collision bytes. |
| 35 | Foreground is the hardcoded `+0x1CA` object redraw path (`d93:2530` / linear `0xFE60`), not source FG/BG.  Normal BG codes such as raw `0xEB` can render over the player because they write nonzero `cA` (`0x02FC`). |

Current rule: separate static level bitmap, runtime actors and true renderer
special cases.  Do not animate whole background groups just because adjacent
tiles form a four-frame-looking block.

## Cleanup Decisions

- `docs/reverse_engineering_status.md` is the current high-level truth document.
- Pass files remain as dated evidence.  They should not be edited into a linear
  tutorial, because their value is showing how conclusions changed.
- Generated JSON/CSV files under `docs/derived_*` are kept as machine-readable
  evidence and should be regenerated from tools, not hand-edited.
- Older docs that say "heuristic" or "visual footprint" should point at the
  runtime-cell model unless they are explicitly describing prototype fallback or
  historical mistakes.
