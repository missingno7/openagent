# Pass 94 — raw 0x63 ceiling crawler / state 0x21 consolidation

Goal: turn the repeatedly revised raw `0x63` notes into one concrete ASM-backed runtime correction, and remove two visible offsets left from the old approximation.

## ASM source

Main state branch in `SAM1_unpacked_linear_8086.asm`:

- `SAM1:0x98D9..0x9AB6` — state `0x21` movement, frame wrapping and laser firing gate.
- `SAM1:0x98E1..0x998B` — candidate-position collision/track probes before turnaround.
- `SAM1:0x99CD..0x9A1E` — frame counter increment and left/right range wrapping.
- `SAM1:0x9A25..0x9A3F` — increment `DS:34DA` and compare it to `DS:34D8`.
- `SAM1:0x9A48..0x9A78` — player-under-column gate.
- `SAM1:0x9A83..0x9AA6` — reset `DS:34DA` and call projectile helper `0x5784`.
- `SAM1:0x9AAB..0x9AB2` — if armed but the player is not in the gate, decrement `DS:34DA` back to armed-minus-one.
- `SAM1:0x9ADB` — call generic contact helper `0x53C4` with `(actor_x, actor_y)` after the firing path.

## Corrections

### Firing gate uses player origin, not sprite centers

The old runtime used a center-to-center check:

```text
abs(player_center_x - actor_center_x) < 16
```

The EXE compares the raw player coordinate fields directly:

```text
actor_x - 0x10 < DS:34EE < actor_x + 0x10
actor_y < DS:34F0
```

Runtime change: `enemy_can_see_player()` now uses strict player-origin bounds for `ceiling_laser`.

### Laser spawn Y is actor_y + 8

The projectile call at `SAM1:0x9A91..0x9AA6` pushes:

```text
x = local actor candidate x
 y = DS:34D0 + 8
 direction = 1
 speed = 8
 object = 0x00C7
```

Runtime change: `spawn_enemy_projectile()` now starts the ceiling laser at `enemy.y + 8` instead of `enemy.y + 16`.  The old offset made the laser appear a half tile too low.

### State 0x21 also has body contact damage

After the firing branch, state `0x21` stores the accepted X and calls helper `0x53C4` with `(actor_x, actor_y)`.  Helper `0x53C4` is the narrow 10x16 generic player hurt/death helper:

```text
player_x..player_x+9 overlaps hazard_x..hazard_x+9
player_y..player_y+15 overlaps hazard_y..hazard_y+15
```

Runtime change: added `contact_hazard_53c4_overlaps_player()` and use it for:

- raw `0x63` ceiling crawler body contact,
- raw `0x78` state-`0x2C` contact hazard,
- raw `0x7F` state-`0x06` contact floater.

This intentionally calls `hurt_player()` rather than `kill_player()`, because `0x53C4` is generic damage unless the player is on the last life.

## Still open

- The candidate-position ceiling-track probe is implemented, but should still be compared against a tiny synthetic map or a DOSBox reference because it uses several `+0x1CC/+0x1CD` byte probes.
- Projectile helper object `0x00C7 -> 0x72/state 0x89` is represented by the decoded vertical laser family, but the exact impact/spark policy remains part of the broader projectile audit.
