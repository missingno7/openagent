# Pass 123 - raw 0xA7 wall-push correction

## Goal

Correct the pass 122 regression where pushing a barrel into a wall destroyed the
barrel, played the score sound, spawned a score popup, and removed the actor.
That behavior was reported as visibly wrong against the original DOS game.

The user observation is treated as a testcase, not as proof.  The ASM was
rechecked to determine which parts are facts and which parts remain a guarded
reconstruction.

## ASM facts rechecked

The raw-barrel actor range is still `SAM1:0x82E3..0x8742`.

Facts that remain valid:

1. `SAM1:0x83C4..0x848A` uses the shrunken player/barrel gameplay rectangle:
   `x+3..x+12` horizontally and `y..y+15` vertically.
2. `SAM1:0x848A..0x84E9` is destructive/score behavior:
   - plays sound `0x04`,
   - adds `0x03E8` score,
   - sets `DS:34E8 = 0x1389`,
   - sets `DS:34DA = 0x10`,
   - sets visible object `DS:34E0 = 0x00AA`,
   - does not write actor X (`DS:34CE`) or direction.
3. `SAM1:0x8542..0x8742` state `0x1389` moves the actor upward by `2 px/tick`,
   clamps Y to absolute `0x10`, decrements the timer, then removes/cleans up the
   actor.

The key correction is negative evidence: this branch cannot be the wall-push
release path.  It exactly explains the broken pass-122 symptom (score + object
`0xAA` + upward removal), and it cannot explain the observed horizontal snap
because it contains no X write.

## Runtime correction

`release_barrel_against_wall()` no longer enters object `0x00AA/state 0x1389` and
no longer gives score or sound.

The wall-blocked push now:

- keeps the actor as raw `0xA7/state 0x1388`,
- marks only the barrel body as pass-through,
- keeps the barrel top usable as a one-way platform,
- flips the barrel direction away from the wall,
- restores the barrel on the free side of the player after the player crosses
  through it.

The free-side snap is still a reconstruction.  It is based on the DOS observation
that the barrel remains in play and shifts away from the wall after the player
passes through it.  The exact ASM store for that snap remains the next research
target.

## Tests

`tools/check_barrel_player_interaction.py` now guards three separate cases:

- a visual edge touch is not a gameplay overlap,
- a blocked side push does **not** trigger score/sound/object `0xAA/state 0x1389`,
- a wall-release barrel is body-pass-through but still top-solid, then snaps to
  the free side and returns to normal body collision.

The old `0x1389` transient test remains, but it constructs that destructive
state directly.  It is no longer reached through `release_barrel_against_wall()`.

## Still open

- exact ASM path/store for the wall-blocked free-side snap,
- exact pushed-off-edge fall start/carry timing,
- helper `0x547C` projectile-hit branch for raw `0xA7`,
- whether individual `0x1389` redraw calls matter in the Python renderer.
