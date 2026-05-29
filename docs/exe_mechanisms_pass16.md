# Pass 16: bank-14 guard hit reaction correction

Pass 15 modelled a player shot from behind as a non-damaging warning turn.  That
was too literal and did not match the in-game behaviour: it is still a real hit.
The extra visible behaviour is that the guard turns to face the player after the
hit.

## EXE evidence used

The bank-14 guard actor family is driven from the same 0x20-byte actor record as
other lightweight actors:

- `DS:34E0 + slot*0x20` holds the active runtime visual/object id.
- `DS:34E2 + slot*0x20` holds horizontal direction.
- `DS:34D6 + slot*0x20` is the animation/frame counter.
- `DS:34DA/34D8 + slot*0x20` are timer/period fields.

The actor branch around `SAM1:0x73D0..0x777F` handles behaviour state `0x16` and
checks the active visual `0x027B`.  At the timer boundary it can rewrite
`DS:34E0` to `0x0271` and resets the frame counter.  Later code scans runtime
cells for `0x027D` and rewrites them to `0x027E`, clears `+0x1CC`, redraws the
neighbouring cells, and ultimately reaches the RIP/grave state.  Separately,
the sight/shoot branches around `0x63CD..0x6455` gate projectile creation by
row, facing direction, and `DS:34E2`.

The important runtime interpretation is: direction rewriting is a hit reaction,
not a replacement for damage.  A projectile that reaches a guard from behind is
still consumed as a successful hit and then the guard direction is flipped.

## Runtime change

- Player shots always apply the bank-14 degradation chain:

```text
32 -> 24 -> 16 -> 8 -> 0 -> RIP(40)
```

- If the shot came from behind, the guard is also flipped toward the player
  before the degraded sprite family is selected.
- A back-shot no longer exits early without damage.
- Shooter status is recalculated after degradation: only base tiles `24` and
  `32` retain shooting behaviour.

This keeps the visible “shot in the back turns around” behaviour while matching
the fact that it is still a real hit.
