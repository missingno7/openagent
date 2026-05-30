# Pass 85 — mines, water, state 0x26 lightning flyer, state 0x06 floater

This pass tightens a few actor/tile behaviours against the current SAM1 ASM notes.

## Raw 0x4D landmine / state 0x17

The idle mine is object `0x0270`.  The draw branch at `SAM1:0x36C2..0x3725`
uses `floor(DS:34D6 / 5)`, while the state-0x17 update wraps non-triggered
mines after `DS:34D6 > 9`.  The decoded atlas cels used by this two-phase blink
are bank 5 tile `23` and bank 5 tile `41`.

Triggered mines still rewrite to object `0x0271` and use the existing short
explosion approximation.

## Raw 0x60 water / runtime visual 0x01F3

Raw mission code `0x60` writes runtime visual `cA=0x01F3`.  The renderer branch
for `0x01F3` alternates bank 4 tile `48` with the paired bank 4 tile `0` graphic.
OpenAgent now overlays that animation from the fixed actor tick so the water no
longer waits on the slower baked static-image cache phase.

The same runtime visual id is also in the interaction dispatcher's hard-death
comparison list, so touching water kills the player immediately.

## Hard-death runtime visuals

The player interaction dispatcher compares the translated runtime cA visual,
not only the raw map byte.  The immediate-death visual ids handled here are:

- `0x01F3` — raw `0x60` water
- `0x025B`
- `0x0265`
- `0x0267`
- `0x0268`

Raw source bytes that translate to those visuals now call `kill_player()` on a
tight overlap.

## Raw 0x6E / state 0x26 lightning flyer

The state branch around `SAM1:0xA70F..0xA894` keeps the actor stationary while a
hold/lightning timer is active and creates object `0x0089` at `(actor_x,
actor_y + 16)`.  OpenAgent now models the visible cycle as:

1. drive for the DS:34D8-derived interval,
2. stop and spawn the lightning object,
3. stay still while the lightning object's `0x1E`-tick lifetime runs,
4. drive again.

This avoids the previous behaviour where the enemy could keep moving while its
lightning was still active.

## Raw 0x7F / state 0x06 floater

Raw `0x7F` maps to object `0x0261`, state `0x06`, with `DS:34D8=2`.  The state
branch decrements that value in the hit path and rewrites to the death object
when it reaches zero.  OpenAgent now marks `0x0261` as shootable with 2 HP.
