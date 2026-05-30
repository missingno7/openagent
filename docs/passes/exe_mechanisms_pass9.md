# EXE mechanisms pass 9: player timing, collision snap and bank 13 frames

This pass fixes the regressions from the first fixed-tick jump implementation.

## Timing / movement speed

The player horizontal step is selected by the EXE routine around `SAM1 0x532D`:

```asm
5330: incw  DS:681E          ; held-direction tick counter
5348: movw  $1, DS:6820      ; ticks 1..2
5355: movw  $2, DS:6820      ; tick 3
5367: movw  $4, DS:6820      ; ticks 4..6
5379: mov   DS:69A4, ax
537c: add   $4, ax
537f: mov   ax, DS:6820      ; ticks >= 7
```

`DS:69A4` is initialized to `4` in the normal path, so the fast steady step is
`8 px` per original DOS logic tick.  Running the earlier 4-pixel ramp at a modern
60 Hz render tick made the game feel too fast.  The runtime now keeps the render
loop independent, but advances player logic at a DOS-like `18.2065 Hz` fixed tick
and uses the EXE-shaped ramp `1, 1, 2, 4, 4, 4, 8...`.

## Jump/fall model

The EXE jump path is still table-driven:

```asm
1a77: cmpw  $0x0f, DS:3500
1a7e: movw  $0x0f, DS:3500
1a86: movw  $0x10, DS:3500
1a9c: decb  DS:69F6
1ab3: mov   DS:69F6, al
1aba: shl   $1, di
1abc: mov   word ptr [DS:69F6 + di], ax
1ac0: sub   ax, DS:34F0
```

The exact initialized DS displacement table is still not fully reconstructed,
but this pass changes the prototype fallback from “all upward for 35 ticks” to a
signed timer-indexed table.  This matters because the real routine can already
move the player down during the jump timer, instead of waiting for a separate
continuous gravity integrator.

## Ground snap off-by-one

The prior landing snap used:

```text
player.y = tile_top - PLAYER_COLLISION_BOTTOM
```

For a 16 px sprite with bottom probe `y + 15`, that places the bottom probe
exactly on the floor tile's first pixel.  Horizontal body probes then read the
floor tile as a body collision, so the player could get stuck while trying to run
on a flat surface.

The corrected snap is:

```text
player.y = tile_top - PLAYER_COLLISION_BOTTOM - 1
```

So the bottom body probe remains in the tile above the floor, while the separate
foot/one-way test still detects the landing when moving downward.

## Bank 13 player frames

The decoded bank 13 atlas is zero-based in the Python renderer.  In the usual
1-based visual atlas numbering:

- tiles 1..4 = walk right
- tiles 5..8 = walk left
- tile 10 = fire right
- tile 11 = fire left
- tile 13 = jump right
- tile 14 = jump left
- tiles 15..16 = death

The previous generic formula accidentally let jump states reach the death tiles.
The runtime now uses explicit mappings for non-walking states:

```text
fire right: bank 13 tile 9  (1-based tile 10)
fire left:  bank 13 tile 10 (1-based tile 11)
jump right: bank 13 tile 12 (1-based tile 13)
jump left:  bank 13 tile 13 (1-based tile 14)
```

Walking still uses the EXE draw formula with `DS:34F6 / 5` for states `0x01` and
`0x05`.
