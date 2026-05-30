# Pass 49: projectile-hit white flash / bright sprite feedback

This pass verifies the short "enemy turns white" feedback directly from the
SAM1 disassembly and separates it from the runtime's behavioural alert timers.

## ASM evidence

The main actor draw loop checks `DS:34CC + slot*0x20` before the normal sprite
path:

- `SAM1:0x22F7` compares `DS:34CC` against zero.
- If it is positive, the draw path uses alternate sprite-source pointers and
  calls the bright/white draw routine path instead of the ordinary actor path.
- `SAM1:0x2F5D` then decrements `DS:34CC` after drawing.

The decoded projectile-hit branches set this counter to three ticks/frames:

- `SAM1:0x5EDE` writes `DS:34CC = 3` after a successful non-lethal actor hit.
- The same write pattern appears in the other decoded hit/reaction branches,
  for example around `0x6172`, `0x64C9`, `0x6804`, `0x69E6`, `0x897F`,
  `0x8ECE`, `0x97DE`, `0x9B06`, `0x9E47`, and `0xA063`.

So `DS:34CC` is not HP and not a movement/AI delay.  It is the temporary visual
hit-flash counter.

## Runtime interpretation

The original EXE has access to alternate bright/white sprite data through its
internal sprite drawing paths.  The decoded PNG atlas used by the Python port
currently exposes only the normal colored cels, so the port emulates the visual
result by replacing every non-transparent pixel of the actor cel with white
while `hit_flash_ticks > 0`.

This is intentionally separate from `alert_ticks`, which the port already uses
for AI pauses/reactions such as lightning flyers and back-shot direction flips.

## Implemented changes

- Added `Enemy.hit_flash_ticks`, mirroring `DS:34CC`.
- Non-lethal projectile hits now set `hit_flash_ticks = 3`.
- Closed-helmet hits on raw `0x24` / object `0x0065` now also flash white but
  still do not damage the actor.
- Bank-14 guard degradation hits set the same flash counter.
- Multi-tile enemies apply the flash to every cel of the composite actor.
