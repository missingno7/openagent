# EXE mechanisms pass 56 — HUD height, mine death crash and PC speaker pitch

## 1. Status bar / bottom overlay

The previous prototype made the HUD a 40px panel.  That was wrong for the game
framebuffer.

Evidence from `SAM1:0x181F1..0x1872A`:

- the routine is an in-frame redraw routine, not a separate UI window;
- it uses `DS:6838 & 7` as a redraw/scroll phase;
- it formats score from `DS:699A/DS:699C` into six digits;
- it reads ammo from `DS:6858` and draws two digits;
- it conditionally blits inventory icons from flags including
  `DS:69F4`, `DS:69EA`, `DS:69EB`, `DS:69E9`, `DS:69EC`;
- it loops over `DS:6A40` and draws one life icon per life;
- the call coordinates and the captured game HUD show an 8-pixel-high black
  strip at the bottom of the 320x200 image.

Implementation changes:

- `STATUS_BAR_H` is now `8`, so the playable camera is 320x192.
- Removed PIL/system-font text from the HUD path.
- Added a tiny bitmap HUD glyph/icon renderer so the bottom strip is drawn as
  pixels like the original.  This is still a stand-in for the exact `DS:6E32`
  glyph/icon table, but no longer uses host fonts and keeps the correct 8px
  footprint.

## 2. Landmine/death respawn crash

Stepping on raw `0x4D` armed mine reached `kill_player()`, then the death timer
called `respawn_after_death()`.  That path still called a removed placeholder
`spawn_player()` and crashed.

Implementation changes:

- Added a real `spawn_player()` helper using `find_spawn()` / `find_world_spawn()`.
- `respawn_after_death()` now calls that helper.
- Hard death now consumes one life immediately and respawns with the remaining
  life count.  Game-over/menu flow is not reconstructed yet, so reaching zero
  restarts the counter to keep RE playtesting possible.

## 3. PC speaker sound pitch

The SND records contain PC speaker PIT divisors, not direct Hz values.  The old
prototype synthesized `value` as Hz, which made effects such as jump sound wrong.

Implementation changes:

- `synthesize_sound()` now uses `1193182 / divisor` for tone frequency.
- The raw ASM sound IDs are still passed through the one-based dispatcher mapping
  introduced in pass 53.

## Still open

- Decode the exact `DS:6E32` bitmap font/icon table and replace the temporary HUD
  glyph masks with the real glyph bytes.
- Reconstruct the real game-over/continue flow after `DS:6A40` reaches zero.
