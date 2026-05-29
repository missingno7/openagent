# EXE mechanisms pass 8 — ticked player jump and reveal-glasses platforms

## Why the old jump could fall through / freeze

The previous prototype still used a continuous `vy += gravity * dt` model and then resolved collision by small correction loops.  That does not match the EXE and it is unsafe around one-way cells: a variable `dt` can step through the exact `prev_bottom <= tile_top <= new_bottom` crossing window, then the correction loop can keep testing the same floor/platform state.

The mission player now runs on a fixed 60 Hz DOS-like tick and moves vertically one pixel at a time for collision purposes.  This makes one-way tests deterministic and removes unbounded `while player_collides()` style recovery in the mission player path.

## Jump evidence from SAM1

Jump is started by the control/overlap routine at `SAM1 0x541B..0x5471`:

```text
541b: cmpb $0x0, DS:69f5     ; do not start another jump while jump flag active
5422: cmpb $0x0, DS:69f3     ; extra state gate
...
546c: movb $0x1,  DS:69f5
5471: movb $0x23, DS:69f6
```

The actual upward phase is handled at `SAM1 0x1A61..0x1AE8`:

```text
1a61: cmpb $0x0, DS:69f5
1a9c: decb DS:69f6
1ab3: mov  DS:69f6, al
1aba: shl  di, 1
1abc: mov  ax, word ptr [DS:69f6 + di]
1ac0: sub  DS:34f0, ax       ; subtract table displacement from player Y
```

So the shape is not a gravity integrator.  It is `DS:69F5` + `DS:69F6=0x23` + a word displacement table.  The current implementation follows that state/tick model and keeps the table in one place (`JUMP_UP_DISPLACEMENTS`) until the initialized DS table bytes are recovered exactly.

Horizontal movement now also follows the EXE-shaped tick logic from routine `0x532D`: held-direction ticks select integer steps `1 -> 2 -> 4` px/tick through `DS:6820`.

## Reveal glasses / hidden platforms

The atlas mapping shows:

```text
raw 0x72 -> bank 5 tile 6   ; glasses
raw 0xD3 -> bank 5 tile 7   ; hidden platform visual
raw 0xD7 -> visual 0x02D3 with foot_solid=1 in the EXE collision table
```

The EXE has a special branch for the glasses visual id.  At `SAM1 0x1CC0` it compares an object visual/id word against `0x0272`:

```text
1cc0: cmpw $0x0272, DS:684e[slot]
1ccb..1dff: special timed draw/effect branch around the actor/player position
```

There is also a raw-object branch at `SAM1 0x1867` comparing `AX` against `0x72` and redrawing neighbor cells around the object.  This matches the observed behavior that glasses affect visibility of nearby/hidden mechanics rather than being an ordinary score item.

Implementation:

* `0x72` is a collectible semantic kind `glasses`.
* Before glasses are collected, raw `0xD3` cells are skipped from the static renderer and use their EXE default collision record: no body and no floor.
* After glasses are collected, raw `0xD3` cells are drawn and their collision writes are replayed as `0xD7`, which is the EXE-derived one-way/foot-solid platform variant for the same visual tile.

This keeps the important distinction between raw map token `0xD3`, raw collision token `0xD7`, and visual tile id `0x02D3`.

## Still open

The exact word table behind `[DS:69F6 + timer*2]` has not yet been reconstructed from the initialized DOS data segment.  The new code is deliberately structured so replacing `JUMP_UP_DISPLACEMENTS` with the real extracted table is a single-data change, not a physics rewrite.
