# Pass 12 — player vertical state, shooting frame selection, and actor timing

## Corrected player jump/fall model

The previous pass still treated the jump as a separate displacement table. The
actual EXE path is simpler and more stateful:

- `BC0E` starts the jump by setting `DS:6EC1 = 1` and `DS:34EA = 0`.
- While `DS:6EC1` is set, the update increments `DS:34EA` and moves the player
  upward by `-byte[DS:34AF + DS:34EA]`.
- At `DS:34EA == 0x0A`, the EXE clears `DS:6EC1` and leaves `DS:34EA = 9`.
- The normal falling routine `B8B3` then increments the same `DS:34EA` and moves
  downward by `+byte[DS:34AF + DS:34EA]`.

So jump and fall share the same table, and the first fall tick after a normal
jump uses index 10, not a fresh index 1. This avoids the strange landing-speed
change caused by restarting the fall counter too early.

Recovered table used by both phases:

```text
index:  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19
value:  8  8  8  4  4  2  2  2  1  1  2  2  2  4  4  8  8  8  8
```

## Corrected shooting frame selection

The player draw routine around `20CE..21C2` computes the sprite source as:

```text
sprite_index = DS:3500 + (DS:34F6 / 5)
```

For non-walking states the render routine resets `DS:34F6 = 1`, so the division
adds zero. The decoded bank-13 atlas is zero-based after the bank pointer
adjustment. Therefore:

- `DS:3500 = 0x0B` renders bank 13 tile `10` — shoot right.
- `DS:3500 = 0x0C` renders bank 13 tile `11` — shoot left.

The earlier implementation used tiles `9/10`, which was one tile too early.

The fire-key handler also only sets `DS:3500 = 0x0B/0x0C` after a shot slot is
actually allocated. If no ammo is available or the jump flag is active, it exits
without changing the player pose. Key release restores `0x09/0x0A`.

## Actor timing

Actor frame counters such as `DS:34D6 + slot*0x20` are tick-based. Updating them
once per modern Tk redraw made enemies animate too quickly. Runtime entity
updates are now paced on the same `18.2065 Hz` DOS tick clock as the player,
while projectile motion remains continuous until the projectile slot update is
fully mapped.
