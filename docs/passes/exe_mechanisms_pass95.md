# Pass 95 - projectile object `0x00C7` / state `0x89` projectile policy

> Pass 96 correction: the helper rewrite `0x00C7 -> object 0x72/state 0x89` is valid, but the direct hard-death rectangle was attributed to the wrong dispatcher branch. State `0x89` calls generic helper `0x53C4`; ordinary object `0x72/state 0x25` is the direct hard-death up-laser branch.

## Scope

This pass follows up pass 94's raw `0x63` ceiling crawler work.  Pass 94 fixed
when and where the crawler fires, but the spawned laser was still treated like a
normal hostile projectile in the Python runtime: a hit called the generic
one-life hurt helper.

The ASM says this particular projectile is not generic damage.

## ASM evidence

### Projectile helper `0x5784`

`SAM1:0x5784..0x5A34` is the common projectile actor allocator.  Most callers
store the object id they pass in, then select a behavior state.  The ceiling
crawler is special:

- raw `0x63` / state `0x21` calls helper `0x5784` with object `0x00C7` from
  `SAM1:0x9A91..0x9AA6`;
- helper `0x5784` checks that input object at `SAM1:0x599A`;
- when it sees `0x00C7`, it rewrites the actor to:
  - `DS:34E0 = 0x0072`,
  - `DS:34E8 = 0x0089`,
  - `DS:34D6 = 1`.

So the visible object family is shared with object `0x72`, but the behavior
state is `0x89`, not the ordinary object-`0x72` state `0x25`.

### State `0x89` hit policy

Pass 96 correction: the state `0x89` branch starts at `SAM1:0xA239`, but the
direct player-death path at `SAM1:0xA656..0xA70C` is reached after the later
state-`0x25` comparison at `SAM1:0xA456`, not from the state-`0x89` branch.

The state-`0x89` moving path reaches `SAM1:0xA439..0xA450`, pushes the beam
coordinates, and calls helper `0x53C4`.  That helper is generic narrow contact
damage: it removes one life and starts invulnerability, entering full death only
through the generic last-life path.

## Runtime changes

- `Projectile` now has explicit hit policy metadata:
  - `hard_death_on_hit`,
  - `hit_w`,
  - `hit_h`.
- Pass 96 correction: raw `0x63` ceiling-laser shots are spawned with:
  - `narrow_hurt_on_hit=True`,
  - `keep_on_player_hit=True`,
  - `hit_w=10`,
  - `hit_h=16`.
- Hostile projectile handling now routes through:
  - `hostile_projectile_hits_player()`
  - `apply_hostile_projectile_hit()`.
- Generic enemy/player bullets still call `hurt_player()` and are consumed on
  impact.
- Pass 96 correction: state-`0x89` beams now call generic `hurt_player()` through
  the narrow `0x53C4` policy and stay visible after the hit.  Direct
  `kill_player()` belongs to ordinary object-`0x72/state 0x25`.

## Intentional limitations

- The exact state-`0x89` map-collision side effects and foreground redraw calls
  around `SAM1:0xA2AF..0xA604` are documented but not fully rebuilt here.
  Pass 96 suppresses the wrong generic wall spark but still leaves those redraw
  details as future work.
- Pass 96 follows up by implementing the object-`0x72/state 0x25` hard-death
  policy and by correcting state `0x89` to generic narrow hurt.
