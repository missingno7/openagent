# Pass 42 — raw 0x75/0x76 state-specific actor mechanics

This pass fills two actor-table gaps that were previously treated as generic walkers.

## Raw 0x75 — state 0x23 / object 0x006D

The special actor table creates raw `0x75` as object `0x006D`, state `0x23`.
The dispatcher branch at `SAM1:0x9FED..0xA15E` shows that it is not a plain
walker:

- it advances the normal walking frame counter `DS:34D6`;
- it writes the candidate X position into `DS:34CE`;
- it calls the contact/collision helper `0x547C`;
- while contact is active it decrements `DS:34DC` from `3`;
- when the counter expires it awards `1000` points, rewrites the actor to
  object `0x00AA`, state `0x1389`, and spawns two side projectiles through
  projectile helper `0x5784` using objects `0x007D` and `0x007E`.

Runtime now models this as a moving contact bomb: it walks with the EXE table's
`2 px/tick`, reverses on the normal ground-walker probes, arms only while
actually touching the player, then explodes into a score popup plus left/right
hostile shrapnel.

## Raw 0x76 — state 0x24 / object 0x0071

The special actor table creates raw `0x76` as object `0x0071`, state `0x24`.
The dispatcher branch at `SAM1:0xA169..0xA236` keeps the actor's X fixed and uses
`DS:34DA/DS:34DC` as a 10-tick timer.  When armed, it checks:

- player center X is inside approximately `actor_x - 4 .. actor_x + 4`;
- player Y is above the actor;
- the one-shot/global fire guard at `DS:69EF` is clear.

On success it calls projectile helper `0x5784` with object `0x0072`, speed `8`,
and direction `-1`.  Runtime now represents this as an upward vertical laser
using the decoded bank-2 laser family `13..15`, moving at `8 px/tick`.

## Runtime changes

- `0x75` and `0x76` are now in `SPECIAL_ACTOR_MODELS` with their real object ids,
  behavior states and timers.
- `0x75` no longer uses the old conservative 1px fallback; it uses table speed 2.
- `0x76` no longer walks or flips on floor checks; it is a stationary up-laser emitter.
- Projectile spawning for both states is separate from the generic horizontal guard
  bullet path.
