# EXE mechanisms pass 10: player motion tables and ledge fall

This pass fixes the prototype to follow the actual player vertical-motion tables initialized by the executable.

## Jump

The jump start still comes from the known writes:

- `546c`: `69f5 = 1`
- `5471`: `69f6 = 0x23`

The important missing part was the initialized jump table.  The update routine does:

```text
1a9c: dec byte [69f6]
1ab3: al = [69f6]
1ab8: di = ax << 1
1abc: ax = word [69f6 + di]
1ac0: [34f0] -= ax
```

The table is initialized at `28ffd..290c6`:

```text
index 1..12  = -8
index 13..18 = -6
index 19..22 = -4
index 23..25 = 0
index 26..27 = 4
index 28..35 = 8
```

Because the routine subtracts the signed word from Y, positive values move upward and negative values move downward.  The jump therefore includes both the upward and downward part of the arc before the ordinary falling routine takes over.

## Falling

The fall routine at `b8b3` increments `34ea`, caps it to `0x13`, then uses byte `[34af + 34ea]` as the downward step.  That table is initialized at `28ed6..28f30`:

```text
index 1..19 = 8,8,8,4,4,2,2,2,1,1,2,2,2,4,4,8,8,8,8
```

After moving down it checks body collision (`+0x1cc`) and, for the later part of the fall, foot/platform collision (`+0x1cd`), then snaps Y to a 16-pixel boundary.

The prototype had a bug where `refresh_grounded_state()` did not clear `grounded` when the foot probes no longer found a floor.  That meant walking off a ledge could keep the player permanently grounded.  It now starts the fall routine when both foot probes lose floor contact.

## Player shooting frames

Bank 13 frame numbers are usually discussed as 1-based.  In that convention:

- frame 10 = shoot right
- frame 11 = shoot left
- frame 13 = jump right
- frame 14 = jump left
- frames 15/16 = death, not jumping

The decoded `Tileset16` arrays are zero-based, so the runtime maps these to tiles `9`, `10`, `12`, and `13`.
