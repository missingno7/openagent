# Mechanics Index

This is the quick orientation table. Detailed evidence remains in `docs/passes/` and `docs/derived_mechanics/`.

| Area | Current implementation | Evidence / notes |
|---|---|---|
| Player movement | EXE-style horizontal step ramp including raw `0x4E` speed bonus, corrected unshifted `6EC1/34EA/34AF` jump/fall table, exact static fall probes, fire pose timing, dynamic-platform crossing landing; pass 130 applies the vertical fall/jump phase before the same-tick horizontal destination probe and pass 131 restores the zero first jump tick plus modulo-16 fall alignment frames | `openagent/player_motion.py`, `openagent/runtime.py`, `openagent/animation.py`, pass 9/12/80-86/90/130/131 notes |
| Player ammo | Starts at 5, pickup +5, capped to 99 | pass 65 |
| Player damage | Generic hurt decrements lives; hard hazards enter death state | pass 55, pass 62, pass 63 |
| Player death | `DS:69F5/69F6` hard-death countdown uses signed table arc: player pops upward, falls down against frozen camera bottom `DS:683A+0xB8`; actor updates continue afterward, so moving platforms can still catch/carry the death sprite through their actor contact branch; then current mission state is fully reset including health/lives | pass 57, pass 62, pass 92, pass 102, pass 105-106 |
| HUD/status bar | 320x200 framebuffer bottom 8 px, `SAM?02.GFX` HUD page 2; score, ammo icon/digits, speed, dynamite, color keys, floppy item and lives use fixed ASM slots | pass 58-61, pass 70, pass 72, pass 93 |
| Menu/table text | 8x8 text renderer prototype using `SAM?02.GFX` pages 0/1 | pass 70 |
| Overworld level 0 | Top-down movement on DOS ticks with ASM flag order, offset-before-write collision, reconstructed `DS:6838/683A` camera registers, dedicated level-0 `CS:0x2E20` parser table, aligned player origin/draw, DS:3500/34F6 walking animation, raw 0x59 marker suppression, origin-based automatic house entry/re-entry, and checked-house completion redraw; exact entrance mapping still prototype | pass 77-78, pass 98-102 |
| Teleporter `0x77` | Paired mission/world teleporter; mission trigger uses ASM +/-2 px alignment, destination release gate, live bank10 28/29 idle and 36..39 warp effect | pass 51, pass 53, pass 88 |
| Laser field `0x82` + computer `0x83` | Computer disables active lasers; laser is hard-death hazard | pass 41, pass 55 |
| Water `0x60` | Runtime visual `0x01F3`; live two-frame render overlay; hard-death on touch | pass 20, pass 23, pass 85, pass 87 |
| Dynamite `0x74` + exit `0x71` | Dynamite pickup; exit blast; broken passable upper/lower door tiles remain | pass 66-68 |
| Landmine `0x4D` | Two-frame idle blink; touching idle mine immediately starts hard death and triggered actor; triggered state keeps a single runtime actor and no longer spawns three persistent extra explosions | pass 53/54/63/87/91/113 |
| Enemy `0x24` | Helmet walker/shooter; vulnerable only in open/stopped phase; closed helmet hit turns without damage/flash | pass 46-49, pass 54, pass 91 |
| Enemy `0x58` | Bank-12 two-high state-0x1F shooter; closed top while walking, opens/fires while stopped, vulnerable only on top tile 19/31 | pass 45, pass 89, pass 91 |
| Enemy `0x63` | Ceiling crawler laser shooter; state-0x21 track edge handling, strict player-origin `actor_x±16` firing gate, `actor_y+8` laser spawn, 0x53C4 narrow body-contact damage, and emitted `0x00C7 -> 0x72/state 0x89` narrow generic-hurt beam | pass 41, pass 94-96 |
| Stationary launchers `0x51/0x52`, `0x3C/0x3D` | Non-solid/non-contact timed launcher family; `DS:34DA` elapsed firing timer charges before row/front gate. `0x51/0x52` fire `0x01D6` from `x±8, actor_y`; `0x3C/0x3D` fire rockets `0x01E8/0x01EC` from `x±16, actor_y`. Their projectiles hurt through the narrow `0x53C4` rectangle but keep flying through the player; `0x547C` owns solid impact/consumption. | pass 26, pass 119-121, pass 129 |
| Pushable barrel `0xA7` | Player/barrel uses ASM `x+3..x+12`, `y..y+15` overlap; successful pushes use broad barrel body collision with a named 4px actor-step reconstruction rather than the player one-pixel substep; unsupported barrel fall now also uses that 4px actor step instead of the player `DS:34AF` table and locks out further side-pushes until landing; wall-blocked push no longer uses the destructive `0x00AA/state 0x1389` score branch, instead keeps raw `0xA7` body-pass-through/top-solid and gates free-side restoration on the ASM shrunken leading-edge crossing with ~10px clearance; exact pushed-off-edge store and exact wall-push caller/store remain partial | pass 116, pass 118, pass 120, pass 122, pass 123, pass 124, pass 125, pass 126, pass 127, pass 128 |
| Dog `0xAE` | Direction-specific walk frame ranges; hit does not flip direction | pass 54 |
| Money bag `0x5B` | Falling pickup state; 5000 points | pass 44 |
| Contact bomb `0x75` | Contact fuse/explosion, 1000 score, shrapnel | pass 42 |
| Up laser `0x76` | Stationary upward laser emitter; emits object `0x72/state 0x25`, which uses the narrow direct hard-death rectangle | pass 42, pass 96 |
| Animated hazards/decor `0x40`, `0x78`, `0xD4` | `0x40` is decorative/non-contact: top animates through bank9 4..7 and lower cel is bank9:1; `0xD4`/`0x78` state-0x2C variants are implemented; `0x78` contact uses only the narrow 0x53C4 helper | pass 43, pass 53/54, pass 91, pass 94, pass 115 |
| Lightning flyer `0x6E` | State 0x26 drive-stop-lightning cycle fixed | pass 69, pass 85 |
| Fire walker `0x6D` | Bank-3 44..47 live contact hazard, immortal to player shots | pass 91 |
| Satellite `0x23` | Rotating non-contact-damage target; player shots remove it for score after durability | pass 91 |
| Projectiles | Player bullets, enemy shots, lasers, and impact visibility partially separated; object-`0x72` states are split (`0x89` ceiling beam = narrow generic hurt, `0x25` up-laser = narrow hard death). Stationary `0x01D6` shots and `0x01E8/0x01EC` rockets now hurt but pass through the player, with consumption reserved for `0x547C` impact. | pass 64, pass 95-96, pass 129 |
| Sound IDs | Jump/fire/hurt/death/no-ammo/pickup IDs separated; synthesis still needs reference comparison | pass 52, pass 56, pass 57, pass 62 |
