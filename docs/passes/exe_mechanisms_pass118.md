# EXE Mechanisms Pass 118 - Raw 0xA7 Player/Barrel Contact Rectangle

## Why this pass exists

Pass 116 fixed the most visible raw `0xA7` symptom: a pushed-off barrel now falls
straight down instead of getting stopped by side-body collision.  The remaining
player/barrel interaction still had a different accuracy problem: the Python
runtime was using full 16x16 sprite overlap to decide when the player was
interacting with the barrel.

The ASM does not do that.  The raw-`0xA7` actor branch uses the same narrow
player-origin gameplay rectangle style used elsewhere in the EXE.

## ASM evidence

The relevant branch is `SAM1:0x82E3..0x8742`:

- `SAM1:0x82E3` selects state `0x1388` for the live raw-`0xA7` actor.
- `SAM1:0x83C4..0x842F` performs the horizontal overlap test.
  - player endpoints: `DS:34EE+3` and `DS:34EE+12`
  - actor endpoints: `actor_x+3` and `actor_x+12`
- `SAM1:0x8432..0x8487` performs the vertical overlap test.
  - player interval: `DS:34F0..DS:34F0+15`
  - actor interval: `actor_y..actor_y+15`
- `SAM1:0x848A` is the player-contact rewrite branch: it plays sound `0x04`,
  adds `0x03E8` to the score accumulator, rewrites state to `0x1389`, sets timer
  `0x10`, and switches the visible object to `0xAA`.
- `SAM1:0x8542..0x8742` is the `0x1389` transient: it subtracts 2 from actor Y,
  clamps at absolute `0x10`, decrements `DS:34DA`, and eventually marks the actor
  slot via `DS:34EB=1` while doing redraw cleanup.

The annotated working copy now names these subparts in:

```text
dissassembly/annotated/SAM1_tick_accuracy_excerpts.asm
```

## Runtime change

`openagent/movement_collision.py` now has explicit raw-`0xA7` helpers:

- `player_barrel_horizontal_overlap()`
- `player_barrel_actor_overlap()`

Those helpers use:

```text
player/barrel X: x+3..x+12
player/barrel Y: y..y+15
```

The runtime now uses this ASM rectangle for:

- detecting player/barrel actor contact,
- dynamic barrel body collision against the player,
- horizontal eligibility when the player lands on or stands on a barrel.

This removes the previous full-sprite contact trigger, which could start a push
while only the decorative sprite edges touched and could make the barrel feel as
if it stuck to the player.

## What is still partial

The actual `0x1388 -> 0x1389` actor-state transition is still not fully modeled
as a separate Python actor state.  The current runtime keeps the reconstructed
`release_barrel_against_wall()` transient ignore/nudge for blocked pushes.

That means this pass narrows the contact geometry to the ASM rectangle, but it
still does not claim full exactness for:

- the score/sound side effects,
- the exact 16-tick `0x1389` animation/redraw cleanup,
- the helper-`0x547C` branch that reaches the other rewrite path,
- DOSBox-verified edge cases involving multiple dynamic actors.

## Regression test

Added:

```bash
python tools/check_barrel_player_interaction.py
```

It checks three cases:

1. visual 16x16 sprite-edge touch is **not** actor overlap,
2. the first true shrunken-rectangle side contact pushes the barrel without
   self-blocking the player,
3. a blocked side push enters the existing transient release path instead of
   hard-locking the player into the barrel.

The normal handoff script now runs this test together with the existing barrel
vertical-fall check.
