# EXE mechanisms pass 101 — overworld player draw, entrance trigger, and completion cels

User testing after pass 100 showed that the island-map collision still felt too
wide in some places and that the level-0 player was missing the original walking
/ turning behavior and automatic house entry.

## ASM evidence

- `SAM1:0xB7D9..0xB8B0` remains the collision source of truth: it samples the
  runtime body byte `+0x1CC` at `DS:34EE+3`, `DS:34EE+12`, `DS:34F0`, and
  `DS:34F0+15`.  The gameplay box is therefore still the 10x16 player-origin
  rectangle, not the full decoded sprite.
- `SAM1:0x20CE..0x21E4` draws the player from the `DS:3500` state and the
  `DS:34F6/34F5` walk counter family.  The draw call uses `DS:34EE/34F0`
  directly; the previous prototype's world-only `(-2,-1)` sprite offset made
  the collision origin appear visually wrong.
- The keyboard/state branches around `SAM1:0x60..0x460` set walk-right state
  `0x01`, walk-left state `0x05`, idle-right state `0x09`, and idle-left state
  `0x0A`.  Up/down movement reuses the current horizontal facing; there are no
  separate island-map up/down cels in this branch.
- The level-0 parser family around the world-map token table has neighbouring
  active/checked house visuals.  In the decoded bank-1 atlas, active house cels
  are 12..15 and the checked/completed variants are 16..19.  Raw `0x4D/0x4E`
  form one two-cell-wide building footprint; `0x4F` and `0x50` are single-cell
  markers.

## Runtime changes

- `find_world_spawn()` now returns the raw `0x59` origin exactly.  It no longer
  adds a prototype `+2/+1` visual fudge.
- `draw_world_player()` no longer draws the sprite at `(-2,-1)`.  The same
  origin is used for drawing and for the ASM 10x16 collision probes, making the
  apparent body size match the EXE model better.
- The world map now draws the normal player animation family via
  `player_tile(state=DS:3500-like state, walk_counter=DS:34F6-like counter)`
  instead of fixed bank-13 tile 0.
- World input updates the draw state:
  - right -> walk-right `0x01`, facing right;
  - left -> walk-left `0x05`, facing left;
  - vertical-only movement keeps the current facing walk state;
  - no movement -> idle-right `0x09` or idle-left `0x0A`.
- `WORLD_ENTRANCE_CODES` now includes `0x4E`, but `world_entrances()` counts an
  adjacent `0x4D/0x4E` pair as one entrance anchor so each episode still exposes
  16 anchors.
- Walking into a building footprint now enters the level immediately.  The old
  Enter/Space path is retained only as a compatibility shortcut.
- Completing a mission records the completed entrance for the current episode
  and returns to level 0 with a release gate so the player does not instantly
  re-enter the same house while still overlapping it.
- Completed entrances are redrawn with bank-1 checked cels 16..19 over the
  baked world map while their active raw source cells are skipped.

## Remaining gaps

- The current entrance-to-level mapping is still row-major.  The original EXE
  dispatch table or flags that map markers to mission numbers still needs a
  dedicated trace.
- The original level-name/table popup on the world map is still not rebuilt.
- The completed-level storage is runtime-local for the playable port; exact save
  / episode progression flags still need tracing.
