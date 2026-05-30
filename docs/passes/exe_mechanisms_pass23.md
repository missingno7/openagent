# Pass 23 — animation timing corrections and actor-table follow-up

## Rotating satellite, raw `0x23` / bank 10 tiles `0..3`

Pass22 incorrectly treated the special actor table field `DS:34D8 = 3` as the
visible frame period.  Looking at the behaviour state `0x20` update shows a
separate actor frame counter path:

- `SAM1:0x977D` checks behaviour state `0x20`.
- `SAM1:0x9785` increments `DS:34D6 + slot*0x20`.
- `SAM1:0x9797` compares the counter with `0x13`.
- If it is above `0x13`, `SAM1:0x97A5` resets it to `1`.

So the satellite should rotate from the actor frame counter, not every 3 DOS
ticks.  The runtime now promotes raw `0x23` into a dynamic `Satellite` entity,
skips the static map marker, advances `frame_counter = 1..0x13`, and displays:

```text
bank 10 tile = floor((frame_counter - 1) / 5), clamped to 0..3
```

This is deliberately slower and follows the same actor-counter style as other
EXE actor animations.

## Bank 4 tile `48 <-> 0`

The actual animated surface case is still the special renderer branch for
runtime visual id `0x01F3`, mapped from raw `0x60` / bank 4 tile `48`.  The EXE
does not expose this as a normal actor slot; draw code compares the object id
against `0x01F3` and tests `DS:6840 == 0x10` to choose between the normal bitmap
and its paired bitmap.

The exact `DS:6840` phase schedule is still not fully reconstructed, but the
previous 8-tick fallback was too slow in play testing.  Runtime/editor preview
now uses a 4-DOS-tick period for the pair:

```text
bank 4 tile 48 <-> bank 4 tile 0
```

## New table data now preserved

The pass23 extractor also writes out a list of special actor table entries that
are clearly game mechanisms but are not yet fully dispatched in the prototype,
including raw `0x56`, `0x58`, `0x63`, `0x24`, `0xAE`, and several trap/object
states.  These are not guessed into gameplay yet; they are kept in
`docs/derived_mechanics/pass23_animation_timing.json` so the next pass can follow
their behaviour states from the EXE rather than re-discovering the table.
