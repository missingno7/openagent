# EXE Mechanisms Pass 38 - Player Projectile Slot and Hit Filtering

## Summary

Player firing is slot based, not cooldown based.  The fire helper at
`SAM1:0x5784` searches for a free actor slot and, for the normal player/guard
shot case, writes:

- `DS:34E0 = 0x0027`
- `DS:34E8 = 0x0007`
- `DS:34E6 = caller speed` (`4` for normal shots)
- `DS:34D6 = 1`

Impact does not spawn an unrelated visual and immediately free the bullet.  The
projectile slot is rewritten, for example at `SAM1:0x5C59..0x5C82`, to:

- `DS:34E8 = 0x1388`
- `DS:34E0 = 0x0187`
- `DS:34E6 = 0`

The runtime now mirrors that lifecycle: a player-owned projectile remains
active through its impact frames, so the player cannot fire another bullet until
the visible impact has completed.

## Hit Filtering

The player bullet does not simply collide with every actor.  The dispatcher
around `SAM1:0x4BD2..0x4ED5` branches by actor object id (`DS:34E0`):

- known shootable ids/ranges are handled by damage branches;
- stationary shooter/trap ids are not damageable and are treated as solid
  indestructible actors in the runtime;
- actors with no decoded damage branch can be passed through until a real EXE
  branch proves otherwise.

The runtime also changed bullet/actor contact from a single end-point test to a
swept segment test over the 4 px/tick movement.  This avoids missing a valid
hit when the projectile crosses the edge of an actor between ticks.

## Open Work

Continue naming exact object-specific hit branches.  The important hard rule is
now preserved: shots block future player shots while their actor slot exists,
and projectile collision is driven by object-id behavior rather than by visual
overlap alone.
