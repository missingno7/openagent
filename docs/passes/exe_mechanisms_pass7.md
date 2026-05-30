# EXE mechanisms pass 7 — player/actor animation and stable floor handling

This pass removes two prototype assumptions that made the runtime visibly diverge from the DOS game.

## Player animation lookup

The player frame is not `bank13[tile chosen by high-level state]` directly.  The draw routine at `SAM1 0x20CE..0x21DF` uses:

```text
if DS:3500 in {0x01, 0x05}:
    DS:34F6 += DS:3506
    if DS:34F6 > 0x13: DS:34F6 = 1
else:
    DS:34F6 = 1

frame = DS:3500 + (DS:34F6 / 5)
sprite_ptr = ES:6D7A + frame * 0xA0 - 0x9D
```

The decoded atlas is zero-based, so the runtime maps this as:

```text
bank = 13
tile = DS:3500 + (DS:34F6 // 5) - 1
```

Important consequence: jump frames `0x0F/0x10` are only used while the EXE jump flag/timer path `DS:69F5/DS:69F6` is active.  They are not a generic falling animation.  Falling off an edge should keep the normal facing/idle/walk state instead of switching into the red jump/death-looking frames.

## Player walk counter constants

Initialization at `SAM1 0x17A1C..0x17A22` sets:

```text
DS:34F6 = 1
DS:3506 = 2
```

The frame counter wraps at `0x13`.  This gives the visible walking frame sequence by grouping counter values in buckets of five.

## Horizontal movement speed evidence

The normal horizontal movement path around `SAM1 0xBAF5..0xBB97` calls routine `0x532D`, then adds/subtracts `DS:6820` from `DS:34EE`.  Routine `0x532D` chooses step values from the held-movement duration:

```text
1 px/tick for early movement
2 px/tick for the next phase
4 px/tick after acceleration
```

The prototype still uses a continuous `MOVE_SPEED`, but now documents that this is standing in for the integer `DS:6820` tick step.

## Actor walker animation

Actor frame counters are stored at `DS:34D6 + slot*0x20`.  Horizontal walkers use:

```text
right-facing range: 0x01..0x13
left-facing range:  0x15..0x27
```

The runtime now keeps a per-enemy `frame_counter` and maps each block of five counter values to one visible tile, instead of using only wall-clock time.

## Floor jitter fix

The earlier prototype resolved downward collision by moving upward one pixel at a time until the floor probe stopped blocking.  For one-way/floor cells this often left the player almost one pixel above the floor.  On the next frame gravity pushed the player back into the floor, causing repeated `grounded -> falling -> grounded` flicker and camera jitter at some zoom/window sizes.

The runtime now snaps landings to the exact top of the blocking floor/platform:

```text
player.y = tile_top - PLAYER_COLLISION_BOTTOM
```

It also has a small post-move ground refresh so a player resting on a floor stays grounded without entering the falling animation state.
