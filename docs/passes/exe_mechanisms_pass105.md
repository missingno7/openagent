# Pass 105 — death camera clamp; platform-carry note superseded

This pass rechecked the `DS:69F5/DS:69F6` hard-death branch after playtesting
showed two inaccuracies:

1. the camera followed the player during the death arc, and
2. the runtime needed to decide whether a falling dead player could still be carried by a moving platform.  Pass 106 corrects the platform interpretation: the original can catch the death sprite.

## ASM evidence

The death branch at `SAM1:0x1A61..0x1AE8` copies the previous player position,
toggles the death/jump cels, decrements `DS:69F6`, applies the signed table step,
and then clamps `DS:34F0`:

```asm
1abc: AX = word [DS:69F6 + (DS:69F6 << 1)]
1ac0: DS:34F0 -= AX
1ac4: if DS:34F0 < 0x10, DS:34F0 = 0x10
1ad3: AX = DS:683A + 0xB8
1ad9: if AX < DS:34F0, DS:34F0 = AX
```

There is no camera-update code inside this branch.  The clamp uses the existing
camera register `DS:683A`; therefore the death fall is bounded by the already
visible playfield bottom instead of scrolling the camera after the dead player.

The moving-platform carry branch lives in the actor contact routine around
`SAM1:0x7FA6..0x8105`.  Pass 105 incorrectly treated it as skipped by the
hard-death branch.  Pass 106 rechecks the ordering and shows why the actor
branch can still catch the death sprite after the death arc has moved it.

## Runtime changes

- `PlayerLifecycleMixin.kill_player()` now asks the app to snapshot the current
  mission camera before setting `player_dead_timer`.
- Non-world `camera()` returns that frozen death camera while `player_dead_timer`
  is active.
- `update_player_death_tick()` clamps Y to `death_camera_y + 0xB8`, plus the
  existing top clamp at `0x10`.
- Moving-platform carry from this pass was superseded by pass 106; carry is
  allowed during death when the actor branch overlap test hits.
- Added `tools/check_death_camera_platform.py` to cover both the camera clamp and
  the platform-carry exclusion.

## Remaining gaps

- The broader mission camera is still a centered helper outside death, not a full
  `DS:6838/DS:683A` reconstruction for normal levels.
- The far restart helper at `0x520:0x011A` still needs a deeper trace for exact
  score/ammo/game-over persistence.
