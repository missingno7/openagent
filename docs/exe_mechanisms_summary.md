# EXE Mechanism Pass Summary

This document condenses `docs/passes/exe_mechanisms_pass*.md` and related collision
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
| 37 | Pushable barrel is dynamic under gravity and can fall after being pushed off an edge. |
| 38 | Player projectile firing is slot-based; impact state keeps the shot active, and bullet hits use object-id filtering plus swept contact. |
| 39 | Moving projectiles are removed when they fully leave the fixed 320x200 active gameplay viewport. |
| 40 | Raw `0x6E` is a state `0x26` lightning flyer: it pauses, spawns object `0x89` below itself, and that state `0x28` actor animates bank2 `36..39`. |
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

| 41 | Re-verified raw `0x63` against state `0x21` at SAM1:0x98d9..0x9ab6; corrected timer arming, under-column gate, and ceiling-track edge probe. |
| 42 | Raw `0x75` is a state-0x23 contact bomb; raw `0x76` is a state-0x24 upward laser emitter. |

| 43 | Raw `0x40`, `0xD4`, and `0x78` promoted as state `0x2B/0x2C` animated actors; `0x78` gets contact hazard handling. |
| 44 | Raw `0x5B` promoted from static money-bag pickup to state `0x29` dynamic falling money bag actor awarding 5000 points. |
| 45 | Raw `0x56` and `0x58` promoted from first-pass walkers to state `0x1E/0x1F` two-high bank-12 shooters; composite hitboxes for `0x24/0x56/0x58` corrected to vertical two-tile actors. |
| 46 | Raw `0x24` / object `0x0065` / state `0x27` rechecked against SAM1:0x12CB2..0x12DC6 and SAM1:0xA89F..0xAFBF. It now uses EXE timers `DA/D8/DC/DE`, direct `0x033B` projectile spawn coordinates, and its non-generic frame ranges `0x01..0x13` / `0xC9..0xDB`. |
| 47 | Raw `0x24` damage behaviour verified: object `0x0065` only dies in the state-`0x27` open/stopped phase (`DS:34DE == 0`). Closed-helmet hits now ping without HP loss; open-helmet hits kill for 1000 points. |
| 49 | Projectile-hit white flash verified: hit branches set `DS:34CC = 3`; the draw loop uses the bright/white draw path while `34CC > 0` and decrements it after drawing. Runtime now mirrors this as `Enemy.hit_flash_ticks`. |


## Pass 48

Audited raw `0x24` / object `0x0065` HP.  The init value `DS:34DC = 3` is not treated as normal HP because state `0x27` reuses the same field as the open-helmet countdown. Removed the misleading generic `0x0065: 3` HP hint and documented the uncertainty.
| 50 | Raw `0x7F` / object `0x0261` / state `0x06` rechecked against `SAM1:0x6864..0x6A21`; it is now a side-collision contact floater/hazard instead of a generic ground walker with floor-ahead ledge logic. |

## Pass 51
- Implemented paired teleporters (`0x77`, runtime visual `0x00B7`) from ASM dispatcher `SAM1:0xD48B..0xD5E8` and main-loop state `DS:69E0/69E2/69E4/69E6`.
- Teleporters work in missions and on overworld maps; trigger alignment, 19 tick delay, target scan, and `±3 px` destination nudge are documented.
| 52 | Continued sound pass: confirmed player jump sound `0x01`, raw `0x5B` falling-bag/drop sound `0x09`, named teleport sound `0x17`, and documented but did not hook the unproven startup/level-entry candidate `0x15`. |
| 53 | Fixed teleport re-entry by requiring the player to leave the destination pad before another `0x77` warp can arm; corrected PC-speaker sound ids to one-based SND indexing; limited raw `0xD4` to its two-frame bank-9 `8..9` animation; implemented raw `0x4D` as the mission landmine (`0x0270` idle -> `0x0271`/state `0x17`). |

| 54 | Raw `0x4D` armed mine is a two-frame idle animated object until triggered; raw `0x24` keeps its helmet closed while walking and animates the top only in the stopped/open phase; raw `0xAE` dog now uses state-0x2A left frame range `0x29..0x3B` and no longer turns from generic hit fallback. |
| 55 | HUD/status bar moved into the 320x200 frame; score/ammo/lives are backed by ASM fields (`DS:699A/699C`, `DS:6858`, `DS:6A40`). Generic hurt now decrements lives with a 0x1E-tick invulnerability window; hard-death hazards such as raw `0x82` lasers and armed `0x4D` mines set death state directly. |

| 56 | HUD/status bar corrected to the original 8px in-frame strip; mine death respawn crash fixed by adding real `spawn_player()`; PC speaker synthesis now treats SND values as PIT divisors (`1193182 / value`) instead of direct Hz. |

| 57 | Reverted PC-speaker synthesis from the bad PIT-divisor assumption back to direct decoded SND pitch words; audited the real HUD DS:6E32 8x8-cell offsets and marked current masks as temporary; added player death animation countdown using bank-13 tiles 14/15 instead of freezing on death. |
| 58 | Decoded the real small HUD/menu asset `SAM?02.GFX` as 8x8 masked EGA cells, fixed the missing `PLAYER_DEATH_TILES` import that crashed the death draw path, and changed the bottom HUD strip to draw digits/life icon from original game pixels instead of temporary PIL masks. |
| 59 | Corrected the SAM?02.GFX decoder to match the Camoto/ModdingWiki 2k 8x8 sprite format: no 3-byte header, 50 * 40-byte masked EGA cells plus 48 bytes padding. HUD digits now use the corrected original UI font cells instead of the previously phase-shifted/noisy decode. |

| 60 | Reverted the bad pass59 SAM?02.GFX no-header decode.  Cross-checked Camoto Studio XML with libgamegraphics/libgamearchive source and the HUD ASM: SAM?02.GFX is a headered tls-sagent-2k block (`50,1,8` header, 50 * 40-byte EGA sprites, 45 bytes padding). HUD digits map to set 0 tiles 0..9 and the life icon to set 0 tile 11. |
| 61 | Fixed HUD 8x8 sprite page selection: Camoto + ASM loader cross-check shows DS:6E32 points at the third SAM?02.GFX 0x800 block, so score/ammo digits and fixed HUD icons must use tiles8 bank 2, not bank 0. |
| 63 | Re-audited raw `0x4D` landmine against `SAM1:0xD0B1..0xD21E` and `0x7782..0x78C1`: stepping on idle object `0x0270` now kills immediately while spawning object `0x0271/state 0x17`; the later frame-`0x0B` hazard remains as secondary explosion contact. Idle mine blink now uses the ASM two-frame `floor(DS:34D6/5)` timing and wraps after frame 9. |
| 65 | Audited player ammo against ASM: new-game init sets `DS:6858 = 5`; raw `0x73`/runtime `0x012D` extra-shots pickup adds `+5`, clamps to `0x63` (99), and plays sound `0x05`. Runtime now starts with five shots and caps ammo/HUD at 99. |
| 66 | Implemented raw `0x74` dynamite and raw `0x71` exit-door flow: `0x027B` pickup sets DS:69F4 and awards 500; `0x027D` door consumes dynamite, plays sound 0x0B, runs a 0x28-tick blast, then opens for level exit. |
| 67 | Corrected post-dynamite exit door: ASM rewrites lower visual 0x027D to passable 0x027E and leaves upper 0x0279 visible, so runtime now draws a broken/open door instead of deleting the whole raw 0x71 footprint. |
| 68 | Corrected the post-dynamite exit door again: ASM `SAM1:0x74D0..0x7523` also rewrites the upper cell from `0x0279` to layer-B visual `0x027A` and clears its collision, so the opened door now draws broken top bank5 tile 33 plus broken/passable lower bank5 tile 37. |
| 69 | Corrected raw `0x6E`/state `0x26` lightning flyer cadence from ASM: `DS:34DE` is the no-movement pause timer, while `DS:34DA == 0` spawns object `0x0089` immediately on the first active tick, then counts to `DS:34D8` before reloading a `0x6E` pause. |
| 70 | Cross-checked Camoto Studio secret-agent.xml and ASM text renderer. Split SAM?02.GFX usage into DS:6E36/6E3A menu-table text pages and DS:6E32 HUD page; added a real 8x8 UI text renderer and removed PIL text from the prototype overworld entrance overlay. |
| 79 | Fixed the pass-74 combat extraction regression by importing `actor_walk_counter_next()` in `combat.py`; added the ASM-backed three-pulse white player hurt visual during the `DS:6A42 = 0x1E` invulnerability window. |
| 80 | Re-audited normal mission movement: preserved `DS:681E` acceleration across direction changes, reset it after blocked movement, fixed the missing one-pixel jump-apex tick, extracted pure tick transitions into `player_motion.py`, and corrected ordinary-jump state IDs to `0x0D/0x0E`. |
| 81 | Corrected normal fall lifetime and ordering: `DS:34EA` now starts at `0x12`, remains capped across landings, standing ticks run the `B8B3` fall pass before jump acceptance, downward displacement is atomic, and opposite Tk direction keys now mirror the ISR's mutually-exclusive flags. |
| 82 | Normal horizontal mission movement now probes the complete `DS:6820` destination step atomically like `SAM1:0xB7D9`; pixel-granular movement remains only as a reconstruction fallback for special raw-`0xA7` barrel overlap. |
| 83 | Fixed dynamic moving-platform landings after atomic fall conversion: player/platform and player/barrel top contacts now use a full downward crossing interval, so an `8 px/tick` fall cannot skip the surface. Re-audited `SAM1:0xB8B3..0xBA49` and recorded the remaining static one-way `+0x1CD` probe-order gap. |
| 84 | Replaced broad static floor snapping with the exact `SAM1:0xB902..0xBA30` fall probes: solid checks use `y+16`, one-way `+0x1CD` checks start only after `DS:34EA > 0x0A`, and a second `y+7` probe rejects late edge overlap. This fixes the episode-1 level-3 raw-`0xD2` fish-sign edge case without regressing dynamic `0x62` platforms. |
| 85 | Corrected raw `0x4D` mine idle blink (`bank5:23/41`), raw `0x60` water fast tick animation and hard-death collision, raw `0x6E` drive-stop-lightning cycle, and raw `0x7F` shootable 2 HP state-0x06 floater. |
| 86 | Re-audited player horizontal acceleration: normal terminal step is `4 px/tick`; raw `0x4E` / runtime `0x0139` sets `DS:69A4=4` for temporary `8 px/tick` speed bonus. Jump/fall remains table-driven by `DS:34AF`; diagonal fall observations should be checked against warmed acceleration state and speed bonus status. |

| 87 | Fixed the pass-85 render integration regression: state-0x17 landmines now draw through the recovered `0x0270/0x0271` object-id frame branch instead of falling back to static raw `0x4D`, and raw `0x60` water is no longer baked into the cached static/foreground layer so the live `0x01F3` overlay is visible. |
| 88 | Re-audited raw `0x77` teleporters against `SAM1:0xD48B..0xD5E8`, `0x2014..0x2039`, and `0x21E4..0x2254`: trigger alignment now uses player-X +/-2 px instead of a broad center test, destination nudge follows the ASM +0x1CC probe (+3 if solid else -3), destination pads stay release-gated until the player leaves them, and live bank10 `28/29` idle + `36..39` warp animation is drawn instead of baking the composite into the static cache. |

| 89 | Re-audited raw `0x58` / object `0x0331` / state `0x1F`: right-facing frame counter starts at `0x3D`, left at `0x01`; renderer now uses bank12 top/bottom cels `16..19/20..23` left and `28..31/32..35` right; runtime now models the `DA/D8/DC/DE` walk-stop-open cycle instead of the old generic walker. |

| 90 | Rechecked raw `0x77` teleporter logic: ASM has no entry-direction branch, only the `DS:69E0/69E2` active cooldown plus the destination `+/-3` X nudge from the `+0x1CC` probe.  Runtime release gating now stays armed until the player's `x+3..x+12` collision footprint leaves the destination pad column, fixing the opposite-direction exit ping-pong.  Also added the `SAM1:0xBC5E..0xBCB8` jump-start headroom probe at `y-3`, `x+3/x+12`, so jumps do not start into a solid tile overhead. |

| 91 | Rechecked raw `0x58` closed/open top-tile logic and no-flash invulnerable hit reaction; added raw `0x6D` bank-3 fire walker, shotable score-target behavior for raw `0x23`, constrained raw `0x40` animation to bank9 `4..7`, and fixed triggered mine explosion draw to bank5 `24..27`. |
| 92 | Rechecked `DS:69F5/DS:69F6` hard-death lifecycle; implemented the signed table-driven upward-then-downward death arc, kept world/actor updates running during death, and reset the mission state after the countdown. |
| 93 | Re-audited the mission HUD/status routine at `SAM1:0x181F1..0x1849E`: added the fixed two-cell ammo icon, moved speed/dynamite/keys/floppy/lives to exact ASM slots, mapped color-specific key icons, and removed the fake glasses HUD icon. |

| 94 | Re-audited raw `0x63` / state `0x21`: firing gate now uses strict player-origin `actor_x±16` bounds, laser spawn is `actor_y+8`, and helper `0x53C4` narrow 10x16 contact damage is shared by the known 0x53C4 contact hazards. |
| 95 | Rechecked projectile helper `0x5784` for raw `0x63`: input object `0x00C7` is rewritten to object `0x72/state 0x89`; pass 96 corrects the damage-policy interpretation for that state. |
| 96 | Re-opened the dispatcher at `SAM1:0xA239..0xA70C`: state `0x89` is the ceiling-crawler beam and calls generic narrow `0x53C4` hurt, while ordinary object `0x72/state 0x25` is the direct hard-death up-laser; object-0x72 solid impacts no longer draw the generic `0x0187` wall spark. |
| 97 | Rechecked object-`0x72` laser overlap at `SAM1:0xA660..0xA6F0`: both state `0x89` generic-hurt beams and state `0x25` hard-death beams now test against the player's 10x16 origin rectangle (`DS:34EE..+9`, `DS:34F0..+15`) instead of the full decoded sprite. |
| 98 | Re-audited level-0 overworld movement/collision: `DS:681C == 1` uses a top-down branch, horizontal motion calls the same `0x532D` step ramp, vertical motion is fixed `4 px/tick`, and collision helper `SAM1:0xB7D9..0xB8B0` samples only runtime body byte `+0x1CC` at the player-origin 10x16 rectangle (`x+3/x+12`, `y/y+15`). |

| 99 | Re-opened level-0 collision construction: `SAM1:0x10811` selects the `CS:0x2E20` world-map parser when `DS:681C == 1`, so level 0 now uses a dedicated collision table instead of mission parser semantics. This fixes raw `0x55` and `0x61` as body-solid on the overworld while keeping `0x30` body-clear per the recovered table. |

| 100 | Re-audited level-0 overworld motion/camera: runtime now preserves the ASM right/left/down/up processing order, checks attempted offsets before writing player position, removes 16x20 sprite-bound pre-clamping, and models `DS:6838/683A` world scroll registers with the `0xAA/0x96/0x50` thresholds and `0x140/0xB8` clamps. |

| 101 | Re-audited overworld player draw/entry: collision remains the ASM 10x16 origin rect, but spawn/draw offsets are now aligned to DS:34EE/34F0; level 0 uses DS:3500/34F6 walking/turning animation, automatic house entry for 0x4D/0x4E/0x4F/0x50 footprints, and checked bank-1 16..19 cels after mission completion. |
| 102 | Fixed three playtest regressions: raw overworld `0x59` is now skipped from static rendering so the live player is not duplicated; completed checked houses remain re-enterable using origin-based entry/release; hard-death restart now keeps the full `load_level(reset_player=True)` state instead of restoring decremented lives. |
| 105 | Rechecked the hard-death branch at `SAM1:0x1A61..0x1AE8`; runtime snapshots the mission camera before `DS:69F5` and clamps the death fall to `DS:683A+0xB8`. Pass 106 corrects the platform-carry interpretation. |
| 106 | Rechecked death/platform ordering: the `DS:69F5` branch reaches the actor update after moving/clamping the death sprite, and moving-platform contact at `SAM1:0x7FA6..0x8105` has no `DS:69F5` guard. Platforms can therefore catch and carry the death animation using the narrow 10px actor/player overlap. |
