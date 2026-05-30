# EXE mechanisms pass 25: projectile sprites, guard firing gate, bank-0 dog facing

## Projectile helper `0x5784`

The shared projectile spawner starts at `SAM1:0x5784`.

Its call convention, as visible from the repeated call sites, is:

```text
push x
push y
push direction      ; +1 or -1
push speed          ; player / guard shots pass 4
push object_id      ; 0 means default shot object
call 0x5784
```

Inside the helper, when `object_id == 0`, the EXE writes:

```text
DS:34E0 = 0x0027
DS:34E8 = 0x0007
DS:34D6 = 0x0001
DS:34E6 = caller speed
```

So player and bank-14 guard shots are the same actor family: object `0x27`, state `0x07`, speed `4 px / DOS tick`.  The decoded atlas representation for this shot is bank 1 tiles `38/39`, not the bank 10 debug tiles used by the previous prototype.

Implemented runtime mapping:

```text
shot right -> bank 1 tile 38
shot left  -> bank 1 tile 39
speed      -> 4 * 18.2065 px/s
```

## Bank-14 guard firing branch

The shooter guard branch around `SAM1:0x63C0..0x6455` does not raycast through the level before firing.  It checks:

```text
(player_y + 8) >> 4 == actor_y >> 4
actor_x < player_x and direction == +1
or
actor_x > player_x and direction == -1
```

When that passes, it resets `DS:34DA` and calls projectile helper `0x5784` with `object_id=0`, `speed=4`.

The previous implementation used the lower half of the player's hitbox for the row check and also added an extra wall raycast.  That made guards stop firing in many normal situations.  The runtime now follows the decoded branch more directly.

## Bank-0 two-tile dog / creature facing

The raw `0xAE` special actor uses object id `0x0353`, state `0x2A`, speed `2 px/tick`, and is a two-tile-wide actor.

For right-facing animation the visible pair is:

```text
(0,4), (1,5), (2,6), (3,7)
```

For left-facing movement the whole two-tile composite must be mirrored.  That means the two halves must be swapped before each 16x16 tile is horizontally flipped:

```text
left frame 0: flip(4), flip(0)
left frame 1: flip(5), flip(1)
left frame 2: flip(6), flip(2)
left frame 3: flip(7), flip(3)
```

The previous runtime flipped each cel but kept the right-facing order, producing the head/body halves in the wrong places.
