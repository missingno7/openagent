# Pass 14: bank-14 guard enemies

This pass adds the bank-14 human guard family as runtime actors instead of
static sprites.

## Map bytes / atlas mapping

The current `TILE_MAP` maps these raw mission bytes to bank 14:

| raw byte | bank 14 base tile | behaviour |
|---:|---:|---|
| `0x38` | 0 | walker, no shooting |
| `0x39` | 8 | walker, no shooting |
| `0x30` | 16 | walker, no shooting |
| `0x67` | 24 | walker + shooting |
| `0x47` | 32 | walker + shooting |

Each 8-tile block is rendered as two 4-frame facing loops: `base+0..3` and
`base+4..7`.  Tile `40` is the RIP/grave sprite.

## EXE evidence

The special-low token table around the actor-backed map codes creates cells with
`c6=2` and no normal body/floor collision.  The active sprite is then driven by
the 0x20-byte actor record:

- `DS:34D6 + slot*0x20`: actor frame counter
- `DS:34E0 + slot*0x20`: active sprite/object id
- `DS:34E2 + slot*0x20`: horizontal direction
- `DS:34DA + slot*0x20`: actor timer
- `DS:34D8 + slot*0x20`: actor timer period
- `DS:34E8 + slot*0x20`: actor behaviour/state

The branch around `SAM1:0x73D0` handles behaviour state `0x16`, increments the
actor frame/timer counters, and at the timer boundary can switch `DS:34E0` from
`0x027B` to `0x0271`.  The interaction dispatcher contains explicit branches
for `0x027B`, `0x027D`, and `0x027E`.  The `0x027B` branch removes the object and
adds `0x01F4` (500) to score; the `0x027E` branch can add `0x61A8` (25000), which
matches the observation that the RIP pickup is worth more than shooting it.

## Runtime implementation

The prototype now treats bank-14 guards as runtime enemies:

- they walk left/right like the other simple walkers;
- the `24` and `32` variants periodically fire horizontal shots;
- player shots degrade `32 -> 24 -> 16 -> 8 -> 0 -> RIP(40)`;
- shooting RIP gives 500 points;
- touching/collecting RIP gives 25000 points;
- their raw marker tiles are skipped from the static background, so moving
  guards are not drawn twice.

The exact original projectile slot/speed table is still not fully reconstructed;
the current hostile shot is a simple horizontal projectile matching the observed
behaviour.
