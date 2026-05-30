# Pass 91 - enemy/object accuracy pass for 0x58, 0x6D, 0x23, 0x40, and 0x4D explosion draw

This pass tightens several actor/render branches that were previously only
partially reconstructed from the special actor table.

## Raw `0x58` / object `0x0331` / state `0x1F`

The actor still uses the previously recovered `DS:34DA/D8/DC/DE` walk -> stop
-> open/fire cycle, but the renderer now distinguishes the two body halves:

- while `DS:34DE` is non-zero, the upper part stays closed:
  - left: bank 12 tile 16,
  - right: bank 12 tile 28;
- the lower part keeps walking through:
  - left: bank 12 tiles 20..23,
  - right: bank 12 tiles 32..35;
- in the stopped/open phase, the upper part advances through:
  - left: bank 12 tiles 16..19,
  - right: bank 12 tiles 28..31.

The player-shot branch now only damages this enemy once the open phase reaches
the final cel: top tile 19 facing left or tile 31 facing right.  Hits while the
cover is closed only turn the actor toward the shot and play the hit sound; they
do not decrement HP and do not set the white hit-flash timer.

The same no-flash invulnerable-hit policy was applied to raw `0x24` / state
`0x27`, whose closed-helmet state is another damage-gated actor.

## Raw `0x6D` fire walker

Raw `0x6D` is now promoted from static map sprite to a live bank-3 fire walker:

- bank 3 tiles 44..47,
- two-pixel horizontal patrol step,
- reverses on ordinary actor collision/floor-edge tests,
- hurts the player on contact,
- is not in the player-projectile damage set, so shots impact but do not kill or
  flash it.

## Raw `0x23` satellite / object `0x0097` / state `0x20`

The rotating satellite remains non-harmful on player contact, but player shots
now hit it as a score target.  It keeps the ASM-backed 3-tick animation period
and a small durability counter before it is removed and awards a score popup.

## Raw `0x40` / object `0x0131` / state `0x2B`

The animated object no longer cycles across bank 9 tiles 1..19.  Its visible
upper cel is constrained to bank 9 tiles 4..7, compressed from the actor frame
counter ranges, and is drawn as the animated upper part of the composite object.

## Raw `0x4D` triggered mine

The triggered landmine branch no longer uses the bank-5 42..44 approximation,
which produced a black square in-game.  It now draws the same visible explosion
cel family as projectile impacts: bank 5 tiles 24..27.
