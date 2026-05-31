# Pass 106 — death arc can be caught by moving platforms

Pass 105 correctly froze the camera during `DS:69F5/69F6`, but it overcorrected
moving platforms by disabling carry while the death flag was set.  Playtesting
against the original shows that a platform can in fact catch the death animation.

## ASM evidence

The top-level player branch reaches the hard-death arc before the actor update:

```asm
1a21: cmp byte [DS:69F5],0
1a26: jne 1a61        ; run death arc
...
1ae8: jmp 1b5d
1b5d: far call 0x520:0x2f6b ; continue actor/world update
```

The moving-platform contact branch around `SAM1:0x7FA6..0x8105` then checks a
narrow player/actor overlap and carries the player.  It checks `DS:6EC1`, but
there is no `DS:69F5` guard in this branch:

```asm
7fa6..7ff5: overlap actor_x..+9 with DS:34EE..+9
7ff5..801c: require DS:34F0+0x10 >= actor_y and actor_y > DS:34F0
801f:       cmp byte [DS:6EC1],0
8030:       DS:34F0 = actor_y - 0x10
8073..80a3: DS:34EE +=/-= actor_speed depending on actor direction
```

So the death branch itself ignores normal tile collision, but the later actor
branch can still snap the falling death sprite to a platform top and move it
horizontally.  That is the original quirk the runtime now preserves.

## Runtime changes

- The fixed mission tick runs `update_player_death_tick()` before actors when
  `player_dead_timer > 0`, matching the observed `1A61 -> 1B5D` ordering.
- Moving platforms no longer gate carry on `player_dead_timer <= 0`.
- Added `platform_carry_contact_asm()` with the ASM narrow test:
  - player X `DS:34EE..+9`, platform X `actor_x..+9`,
  - player base `DS:34F0+0x10`,
  - platform top must be below player origin and at/above player base.
- When the branch hits, runtime snaps `player.y = platform.y - 16` and carries X
  by the platform step, even during death.
- `tools/check_death_camera_platform.py` now asserts that the death sprite is
  caught/carried instead of excluded.

## Remaining gaps

- The mission camera is still frozen during death as in pass 105, but normal
  mission `DS:6838/683A` camera registers are not fully reconstructed outside
  this branch.
- `DS:6EC1` is approximated by the runtime player jump state; the new platform
  catch helper documents the exact ASM condition but does not yet model every
  possible transient `6EC1` edge case.
