# Mechanics Index

This is the quick orientation table. Detailed evidence remains in `docs/passes/` and `docs/derived_mechanics/`.

| Area | Current implementation | Evidence / notes |
|---|---|---|
| Player movement | EXE-style horizontal step ramp including raw `0x4E` speed bonus, normal `6EC1/34EA/34AF` jump/fall table, exact static fall probes, fire pose timing, dynamic-platform crossing landing | `openagent/player_motion.py`, `openagent/runtime.py`, `openagent/animation.py`, pass 9/12/80-86/90 notes |
| Player ammo | Starts at 5, pickup +5, capped to 99 | pass 65 |
| Player damage | Generic hurt decrements lives; hard hazards enter death state | pass 55, pass 62, pass 63 |
| Player death | Death countdown and two-cel death draw path; still needs full state audit | pass 57, pass 62 |
| HUD/status bar | 320x200 framebuffer bottom 8 px, `SAM?02.GFX` 8x8 EGA sprites, HUD page 2; renderer isolated in `openagent/hud.py` | pass 58-61, pass 70, pass 72 |
| Menu/table text | 8x8 text renderer prototype using `SAM?02.GFX` pages 0/1 | pass 70 |
| Teleporter `0x77` | Paired mission/world teleporter; mission trigger uses ASM +/-2 px alignment, destination release gate, live bank10 28/29 idle and 36..39 warp effect | pass 51, pass 53, pass 88 |
| Laser field `0x82` + computer `0x83` | Computer disables active lasers; laser is hard-death hazard | pass 41, pass 55 |
| Water `0x60` | Runtime visual `0x01F3`; live two-frame render overlay; hard-death on touch | pass 20, pass 23, pass 85, pass 87 |
| Dynamite `0x74` + exit `0x71` | Dynamite pickup; exit blast; broken passable upper/lower door tiles remain | pass 66-68 |
| Landmine `0x4D` | Two-frame idle blink; touching idle mine immediately starts hard death and triggered actor | pass 53/54/63/87 |
| Enemy `0x24` | Helmet walker/shooter; vulnerable only in open/stopped phase; closed helmet hit turns without damage/flash | pass 46-49, pass 54, pass 91 |
| Enemy `0x58` | Bank-12 two-high state-0x1F shooter; closed top while walking, opens/fires while stopped, vulnerable only on top tile 19/31 | pass 45, pass 89, pass 91 |
| Enemy `0x63` | Ceiling crawler laser shooter; track edge handling; immediate fire when armed/player below | pass 51-era fixes and earlier 0x63 notes |
| Dog `0xAE` | Direction-specific walk frame ranges; hit does not flip direction | pass 54 |
| Money bag `0x5B` | Falling pickup state; 5000 points | pass 44 |
| Contact bomb `0x75` | Contact fuse/explosion, 1000 score, shrapnel | pass 42 |
| Up laser `0x76` | Stationary upward laser emitter | pass 42 |
| Animated hazards/decor `0x40`, `0x78`, `0xD4` | `0x40` upper animation constrained to bank9 4..7; `0xD4`/`0x78` state-0x2C variants implemented | pass 43, pass 53/54, pass 91 |
| Lightning flyer `0x6E` | State 0x26 drive-stop-lightning cycle fixed | pass 69, pass 85 |
| Fire walker `0x6D` | Bank-3 44..47 live contact hazard, immortal to player shots | pass 91 |
| Satellite `0x23` | Rotating non-contact-damage target; player shots remove it for score after durability | pass 91 |
| Projectiles | Player bullets, enemy shots, lasers, impact visibility partially separated | pass 64 |
| Sound IDs | Jump/fire/hurt/death/no-ammo/pickup IDs separated; synthesis still needs reference comparison | pass 52, pass 56, pass 57, pass 62 |
