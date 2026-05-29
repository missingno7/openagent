# Gameplay Research

## Game Modes

Secret Agent has at least two gameplay modes:

- **Island/world map**: top-down movement on block 0 of each `SAM?03.GFX`
  archive. The player moves around the island and chooses a level entrance.
- **Mission level**: side-view platforming in blocks 1-16 of the same archive.

This matters because level 0 must not use platform physics. It is a separate
mode with its own collision and entrance handling.

## World Map Findings

The editor/Camoto mapping identifies `SAM?03.GFX` block 0 as
`map2d-sagent-world`. The world-map code table differs from normal levels.

Important observed world-map codes:

- `0x59`: Agent/world-map player icon, bank 13 tile 0. Appears once per episode
  map and is a good initial spawn marker.
- `0x4D` + `0x4E`: two-tile base/entrance graphic. Count `0x4D` as one level
  entrance; `0x4E` is the right half.
- `0x4F`: flag/building entrance.
- `0x50`: arch/bunker entrance.
- `0x55`: water.
- `0x56`, `0x57`, `0x58`, `0x61`, `0x62`, `0x63`, `0x64`, `0x65`, `0x66`,
  `0x67`, `0x68`: coast/edge pieces. This is world-map table only; mission
  code `0x65` has a separate enemy meaning.
- `0x42`, `0x43`, `0x44`, `0x45`, `0x46`, `0x47`: tree/forest tiles. These
  should block world-map movement.
- `0x77`: bridge/tunnel composite.

Counting `0x4D`, `0x4F`, and `0x50` in row-major order gives exactly 16
entrances for each episode. The current prototype maps those candidates to
levels 1-16 in that order until the original EXE entrance table is recovered.

The current `openagent.semantics` world collision table keeps grass/path codes
walkable and blocks water, coast, and tree/forest codes. This fixes the first
known bad interpretation on episode 1 map 00: grass is passable, trees are not.

The level row layout is not a gameplay collision layer split. A row beginning
with `*` maps onto the previous visual row and gives the same cell a second map
code. Runtime code should therefore query both BG and `*` rows for a cell and
then apply code semantics. Treating only `bg_raw_for_y` as gameplay data causes
bad starts and missed objects.

## Disassembly Clues

All three `SAM*_strings.txt` files contain the same user-facing clues:

- "You can only save your game on the island map."
- "If you get stuck in a level, ... the island map and restart."
- "Warp to which level?"
- "Press PgUp-PgDn Esc-Exit" in help/story panels.
- "Press SPACE when this is ..." in joystick calibration.
- "Keys match colored doors."
- "Extra shots"
- "Pushable barrel."
- "Money bag."

The save restriction confirms the island map is not just a visual level select
screen. It is part of the main game state.

The unpacked executables also contain direct literal uses of several important
tile/object codes:

- all three disassemblies write literal `0x59` into object/map structures;
- all three disassemblies write literal `0x62`, matching the moving-platform
  hint and atlas graphic;
- all three disassemblies compare and write literal `0x65`, matching the
  riding-enemy hint.

These references are not yet a full reconstruction of the update routines, but
they make those codes stronger than visual guesses.

The current passability table also records a small data-proven set of
environment codes:

- `0x1E`, `0x99`, and `0xBE` appear directly underneath valid `0x59` player
  start markers in the original level data, so they cannot behave like ordinary
  solid wall cells at spawn.
- `0x35`, `0x36`, and `0x37` are background shade variants handled specially by
  the original draw code and are treated as passable overlays.

## Mission Code Semantics

`openagent.semantics` now records the current best-known mission-level meanings:

- `0x59`: player start, bank 13 tile 0. It appears in every raw level block
  across all three episodes; episode 3 level 3 has two adjacent markers, so the
  runtime currently uses the first one.
- `0x62`: moving platform, bank 6 tile 25.
- `0x65`: riding/moving enemy, bank 2 tile 16.
- `0x5B`: money bag score pickup, bank 5 tile 18.
- `0x84`: score pickup, bank 5 tile 4.
- `0xA7`: pushable barrel, bank 6 tile 24.
- `0x73`: extra shots/ammo pickup, bank 9 tile 0.
- `0x2B` -> `0x2C`: green key and green door, bank 3 tiles 20/21.
- `0x2D` -> `0x2E`: red key and red door, bank 3 tiles 22/23.
- `0x2F` -> `0x34`: blue key and blue door, bank 3 tiles 24/25.

Evidence levels are intentionally kept in the code table. The broad categories
for keys, doors, ammo, barrel, and money bag are backed by repeated manual/help
strings in all three episodes. The exact state changes, score values, movement
speeds, collision masks, and animation frame choices still need to be recovered
from the executable routines rather than guessed.

Current active-object notes:

- `0x62` is now extracted as an active mission-level moving platform, not a
  solid tile. The prototype moves it horizontally, reverses direction when its
  16x16 rectangle hits a solid map cell, and carries the player when standing on
  top. This matches the observed simple left/right behavior; exact speed and
  edge cases still need confirmation from the update routine.
- `0x65` is extracted as an active enemy marker, but movement/contact behavior
  is not implemented yet. The disassembly has repeated direct comparisons
  against literal `0x65` in actor/render/update paths.
- World-map `0x62` is not a platform. It remains a world-map coast code because
  the world map uses a separate code table.

The most useful executable findings so far:

- The routine around `0xD92F` in `SAM1_unpacked_linear_8086.asm` converts pixel
  coordinates to 16x16 grid coordinates, bounds-checks them against `0..39`,
  and reads a map buffer at offset `+0x1C6`. This is a key place to reconstruct
  real tile queries.
- The render/update path around `0x22EF..0x2F55` iterates actor records in
  32-byte slots (`index << 5`) and dispatches behavior/rendering by the actor
  code stored around `+0x34E0`. This confirms moving things should become
  runtime entities rather than remain normal solid map cells.

## OpenCrystalCaves Architecture Notes

OpenCrystalCaves is still useful as a runtime pattern:

- `State` handles fade-in/fade-out and high-level UI states.
- `GameState` owns pause/menu/warp panels and transitions between main level
  and platform levels.
- `GameImpl::update()` updates in this order:
  1. level systems such as moving platforms and entrances;
  2. actors/items;
  3. missile/projectile;
  4. enemies;
  5. hazards;
  6. player touches and player update.
- `GameRenderer::render_game()` draws background, back tiles, back objects,
  enemies, player, front tiles, front objects, completion border, and statusbar.
- Animated tiles are represented as a base sprite id plus a frame count and
  rendered with `(game_tick / 2) % sprite_count`.
- Animated objects expose `get_sprite(ticks)`, while many actors/enemies keep
  local frame counters in their update methods.
- Player animation is state-driven: death, direction, walking, jumping/falling,
  shooting/recoil, reverse gravity, hurt flashing, and tough red tint all alter
  sprite selection or palette.

For OpenAgent, the equivalent architecture should split world-map state and
mission-level state instead of treating world-map block 0 as a platform level.

## Current Prototype Behavior

`openagent.runtime` now has two modes:

- level index `0`: top-down world map, initial spawn from code `0x59`, entrances
  from codes `0x4D`, `0x4F`, and `0x50`;
- level index `1..16`: side-view platformer prototype.

The world map collision is still heuristic. It blocks water/coast codes and
tree/forest codes and allows movement on interior terrain/paths. The entrance
order is data-derived but not yet proven against original code.

## Next Research Targets

1. Identify `SAM?02.GFX` 8x8 sprite semantics. `openagent.sprites` now decodes
   the three 50-sprite banks, and `artifacts/sam102_8x8_atlas.png` shows UI
   glyphs, digits, small colored icons, and likely HUD/control markers.
2. Recover the original world-map movement constraints and entrance-to-level
   mapping from EXE code.
3. Build a gameplay semantics table for normal map codes: solid, platform,
   decorative, pickup, enemy, hazard, door, teleporter, exit, and blueprint.
4. Port OCC's state/update/render separation into OpenAgent once Secret Agent
   entity semantics are more complete.
