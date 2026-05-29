# EXE mechanisms pass 17 — actor tick speed, moving-platform direction, grave score

## Actor speed model

The earlier runtime stored moving actors as pixels/second.  That is not how the
DOS EXE stores them.  The actor record has a word at:

```text
DS:34E6 + slot*0x20
```

The common actor dispatcher uses this as a literal per-game-tick pixel step.  In
SAM1 disassembly this field is written with small constants in several actor
branches:

```text
5EF8: mov word ptr [34E6+slot], 1
617F: mov word ptr [34E6+slot], 2
64D6: mov word ptr [34E6+slot], 3
```

Therefore OpenAgent now updates simple walkers/platforms on the existing DOS tick
clock and moves them by integer pixels per tick instead of by `speed * dt`.

Current implemented raw-code mapping:

```text
0x65 -> 1 px/tick
0x75 -> 1 px/tick
0x76 -> 1 px/tick
0x6E -> 2 px/tick
bank14 guards -> 1 px/tick
moving platform 0x62 -> 1 px/tick
```

The full map-code -> actor-behaviour-type table is still not completely decoded,
but the runtime model now matches the EXE storage shape, so adding more recovered
actor types is just a table update.

## Moving platform initial direction

The visible moving platform (`raw 0x62`) now starts with `DS:34E2 = -1` style
movement, i.e. left.  This matches the original-game observation and removes the
previous default-right prototype behaviour.

## Bank-14 grave/RIP score

The previous pass accidentally assigned the bank-14 RIP/grave pickup a very high
bonus, which made the score popup fall back to the largest available bank-10
popup (`10K`).  In-game verification shows the grave pickup is `1000`, while
shooting it remains `500`.

Implemented:

```text
shoot grave/RIP -> 500 points
collect grave/RIP -> 1000 points, bank 10 tile 19 popup
```
