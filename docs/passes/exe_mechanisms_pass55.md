# EXE mechanisms pass 55 — in-frame HUD/status bar and player damage vs hard death

## Status/HUD overlay

The game does **not** draw the score/ammo/lives UI as an extra window area below
the 320x200 game screen.  SAM1 redraws it into the same framebuffer.

Important ASM anchors:

- `SAM1:0x181F1..0x1872A` is the status redraw routine.
- It formats the score from `DS:699A/DS:699C` as six decimal digits.
- It reads `DS:6858` for the two ammo digits.
- It conditionally draws inventory/status icons from byte flags such as
  `DS:69F4`, `DS:69EA`, `DS:69EB`, `DS:69E9`, `DS:69EC`.
- It loops over `DS:6A40` and draws one life icon per remaining life.
- New-game/init paths set `DS:6A40 = 3`, so three lives is the verified start
  value.

Runtime change:

- The prototype now uses a 320x200 screen with a black bottom status band inside
  the rendered frame.
- The camera/playfield height is now `200 - 40 = 160` logical pixels.
- The separate Tk-only HUD strip below the frame was removed.
- The bar currently uses text/glyph approximations rather than fully recovered
  original UI tiles, but the counters and placement model match the EXE-level
  structure: score, ammo, lives and inventory flags are in-frame.

## Hurt vs death

There are at least two important player-harm paths in the ASM.

### Generic hurt helper

Anchors:

- `SAM1:0x53F4..0x5476`
- `SAM1:0x6B28..0x6B71`

Observed behavior:

- If `DS:6A40 > 1`, the game:
  - checks that the player is not already invulnerable/dead,
  - sets `DS:6A41 = 1`,
  - sets `DS:6A42 = 0x1E`,
  - decrements `DS:6A40`,
  - stores `DS:6832 = 0xFFFF`,
  - stores `DS:34EC = 5`,
  - plays sound `0x07`.
- If `DS:6A40 <= 1`, it sets the death state instead:
  - `DS:69F5 = 1`
  - `DS:69F6 = 0x23`

Runtime change:

- `hurt_player()` now models this as lives, not a vague flash-only effect.
- Generic enemy body contact and helper-`0x53C4` contact hazards remove one life
  and give a short invulnerability window.
- The runtime starts with three lives.

### Hard-death tile/actor dispatcher

Anchors:

- `SAM1:0xA6F2..0xA707` sets `DS:69F5/69F6` directly for one actor-contact
  branch.
- `SAM1:0xD1ED..0xD205` sets the same death state after the armed mine branch.
- `SAM1:0xD221..0xD254` compares runtime cell visuals including:
  - `0x01F3`
  - `0x025B` — laser field generated from raw `0x82`
  - `0x0265`
  - `0x0267`
  - `0x0268`
  and then sets `DS:69F5 = 1`, `DS:69F6 = 0x23`, sound `0x16`.

Runtime change:

- Raw `0x82` laser field now uses `kill_player()`, not generic one-life hurt.
- Armed landmine `0x4D` explosion frame now uses `kill_player()`.
- Generic body-contact enemies still use the hurt/life decrement path.

Open item:

- The exact original icon/glyph tiles for the bottom bar still need a dedicated
  extraction pass from the UI font/sprite sheet around the `0x6E32` surface and
  the blit offsets used by `0x29C2:*` calls.  The current implementation is
  mechanically correct but visually approximate.
