# EXE mechanisms pass 54 – 0x4D mine idle, 0x24 helmet phase, 0xAE dog frames

This pass fixes three visual/behaviour mismatches that showed up during play-testing.

## Raw `0x4D` landmine

Raw `0x4D` writes runtime visual/object `0x0270` in mission maps.  The draw path for
objects in the `0x0259..0x0270` family uses `DS:34D6 / 5` to select the visible cel,
so the armed mine is a small two-frame animated object, not a full state-`0x17`
explosion sequence.

Runtime change:

- idle `0x4D` keeps object `0x0270` and loops only bank 5 tiles `41,42`;
- the triggered state `0x17` sequence starts only after player overlap rewrites the
  actor to object `0x0271`;
- frame `0x0B` remains the hazard/damage moment for the triggered sequence.

Relevant ASM anchors:

- draw family `0x0259..0x0270`: `SAM1:0x36BD..0x3725`;
- object `0x0271` draw family: `SAM1:0x3728..0x378B`;
- state `0x17` frame/hazard branch: `SAM1:0x7782..0x78C1`.

## Raw `0x24` helmet enemy

The port previously animated the top helmet cel together with the lower/body cel.
That made the visor appear to open continuously while the enemy was walking.

Runtime change:

- while `DS:34DE` / `phase_ticks` is non-zero, the top cel is held on closed helmet
  tile bank 2 tile `40`;
- only during the stopped/vulnerable phase does the top cel use the `40..43` opening
  frames;
- the lower/body part continues to animate independently through bank 2 tiles
  `44..47`.

This keeps the previously verified damage rule intact: closed/walking helmet pings,
stopped/open helmet is killable.

## Raw `0xAE` dog / two-wide creature

State `0x2A` does not use the generic left-walk frame range.  The ASM uses:

- right-facing `DS:34D6 = 0x01..0x13`;
- left-facing `DS:34D6 = 0x29..0x3B`.

The generic actor code used `0x15..0x27` for left-facing movement, which compressed
to a single visible frame in the decoded bank-0 dog renderer.

Runtime change:

- added a dedicated state-`0x2A` frame counter;
- left-facing dog movement now animates through all four frames;
- non-lethal projectile hits no longer force `0xAE` to face away from the shot.  The
  ASM projectile-hit branch flashes/decrements HP; the visible turn in the port was
  a generic fallback artefact.

Relevant ASM anchors:

- state `0x2A` movement/frame ranges: `SAM1:0x8745..0x8ACE`;
- non-lethal hit flash/HP branch: `SAM1:0x896F..0x899E`.
