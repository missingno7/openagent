# Pass 62: sound ID corrections and death-loop freeze fix

## Sound IDs rechecked against SAM1_unpacked_linear_8086.asm

The previous pass accidentally reused sound `0x16` for the denied/no-ammo
case.  That is wrong: `0x16` is the player death sound.

Confirmed call sites:

- `SAM1:0x016F..0x017A`
  - checks `DS:6858 == 0` before player fire
  - pushes `0x14`
  - calls the common PC-speaker routine at `0x287E`
  - this is the real denied/no-ammo sound

- `SAM1:0x02B0..0x02BE` and `SAM1:0x0B92..0x0BA0`
  - decrements ammo
  - pushes `0x02`
  - this is the normal player shot sound

- `SAM1:0x5437..0x5455`
  - generic non-lethal player damage path
  - decrements `DS:6A40`
  - sets invulnerability `DS:6A41=1`, `DS:6A42=0x1E`
  - pushes `0x07`
  - this is the hurt/life-lost sound

- `SAM1:0x5463..0x5471`
  - last-life damage path
  - pushes `0x16`
  - sets `DS:69F5=1`, `DS:69F6=0x23`
  - this is the player death sound

- `SAM1:0x1A8C..0x1AA0`
  - death-state loop
  - when `DS:69F6 == 0x23`, pushes `0x16` once at the start of the death animation
  - then decrements `DS:69F6`

Runtime changes:

- `SOUND_NO_AMMO` corrected from `0x16` to `0x14`.
- Added `SOUND_PLAYER_DEATH = 0x16`.
- `SOUND_HURT` corrected to `0x07`.
- `SOUND_FIRE` now uses the player-shot ID `0x02` instead of the hurt ID.

## Death animation freeze

The Tk runtime was stopping after death because the tick loop returned directly
after `respawn_after_death()`, before scheduling the next `root.after(...)`.
This looked like the original death animation had finished and then the game
froze, while UI actions such as level switching still worked.

The tick loop now respawns and continues to the draw/schedule tail, so the main
loop keeps running.

## Cleanup

Removed temporary PNG research dumps from the project root.  Generated asset
inspection images should stay outside the packaged project or under a dedicated
ignored scratch directory.
