# EXE mechanisms pass 131: corrected DS:34AF vertical table indexing

Focus: continue the one-tile-opening player movement investigation from pass 130.
The user hypothesis was that the DOS game may naturally create moments where the
fall/jump arc aligns the player origin to 16px tile boundaries.  Treating that as
a testcase led to a concrete ASM transcription error in our Python table.

## ASM finding

The vertical displacement table is not initialized at `0x34AF`.  The init path
writes bytes `0x34B0..0x34C2`:

```asm
28ed6: movb $0x00, 0x34b0
28edb: movb $0x08, 0x34b1
28ee0: movb $0x08, 0x34b2
28ee5: movb $0x08, 0x34b3
28eea: movb $0x04, 0x34b4
...
28f30: movb $0x08, 0x34c2
28f35: movb $0x12, 0x34ea
```

But both fall and jump read it as `byte[0x34AF + DS:34EA]` after incrementing the
counter:

- `SAM1:0xB8B6..0xB8D8` increments/caps `DS:34EA`, reads `0x34AF + counter`, and
  adds it to `DS:34F0` for falling;
- `SAM1:0xBD06..0xBD36` increments `DS:34EA`, rewinds `0x0A` to `0x09`, reads the
  same table, negates it, probes `B7D9`, and subtracts it from `DS:34F0` for jump
  ascent.

Therefore `DS:34EA == 1` reads `0x34B0`, whose value is **0**, not 8.  The old
Python table was shifted by one slot.

## Correct table behavior

With the corrected indexing, a normal jump's upward displacements are:

```text
0, 8, 8, 8, 4, 4, 2, 2, 2, 2 = 40px total
```

After the apex, `DS:34EA` remains at 9, so falling resumes with:

```text
1, 1, 2, 2, 2, 4, 4, 8, 8, 8...
```

This matters for one-tile openings.  A tile-aligned jump start minus 40px leaves
the player origin at `+8 mod 16`.  The first five fall steps add another 8px
(`1+1+2+2+2`), creating a real `0 mod 16` frame where the 16px-tall player body
can fit exactly into a one-cell-high opening.  The shifted Python table produced
`1+2+2+2+4 = 11px` over that same interval and skipped the alignment frame.

## Python changes

`openagent/game_constants.py::PLAYER_VERTICAL_STEP_TABLE` now mirrors the EXE
indexing:

```python
PLAYER_VERTICAL_STEP_TABLE = (
    0,
    0, 8, 8, 8, 4, 4, 2, 2, 2, 1, 1, 2, 2, 2, 4, 4, 8, 8, 8,
)
```

`tools/check_player_motion_accuracy.py` now protects both pieces:

- counter 1 must be a 0px jump tick and counter 2 an 8px tick;
- a synthetic jump/fall against a one-cell wall opening must produce a
  tile-aligned frame that can enter the opening.

## Status

This fixes a real ASM-derived bug.  The broad outer ordering around `BC0E` and
the horizontal control wrapper is still marked `asm_partial`, but the table data
itself is now directly tied to `SAM1:0x28ED6..0x28F35`, `SAM1:0xB8B3`, and
`SAM1:0xBD06..0xBD36`.
