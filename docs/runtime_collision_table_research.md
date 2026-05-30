# Runtime collision table extraction pass

This pass fixes a mistake in the earlier extractor.  The previous tool stopped at
only the first token table, `CS:2e20`, which covers the ASCII-like `0x41..0x7a`
range.  That table is not the whole map-code table used by the current
`SAM?03.GFX` one-byte mission levels.

The EXE contains three relevant token-table groups that call the same runtime
cell setter:

| CS token table range | Distinct tokens | Meaning observed |
| --- | ---: | --- |
| `0x2e20..0x2e86` | 52 | first parser context; excluded from current one-byte mission collision resolution |
| `0x3a59..0x3a8f` | 28 | additional low/special codes |
| `0x66f9..0x68a7` | 216 | main SAMLEV-style one-byte mission map codes |

The new extractor is `tools/extract_sa_runtime_collision_calls.py`.  It finds the
runtime cell setter automatically per EXE (`0x1059e` in SAM1, `0x1062e` in
SAM2/SAM3) and extracts every call site, not just the first decision routine.
All three episodes now yield 350 runtime-cell writes for 244 unique token bytes.

Important confirmations:

- Current map code `0x70` resolves through the later table to two non-solid
  runtime writes.  The earlier `CS:2e20` `0x70` entry was a different parser
  context and was the reason for the wrong previous conclusion.
- `0x18`, `0xEA`, `0xEB`, and `0xEC` are non-solid in the runtime table.
- `0xD2` writes four runtime cells.  The two cells at `x-1` have
  `foot_solid=1` and `body_solid=0`; the two cells at `x` are fully passable.
  This is not a hand-coded special case anymore: it comes from the EXE setter
  calls for token `01 d2`.
- Composite objects are represented by multiple runtime setter calls from one
  token match.  Therefore collision must be derived from the runtime-cell writes,
  not from the raw anchor byte alone.

Generated files:

- `docs/derived_collision_tables_all/SAM1_runtime_collision_calls.csv`
- `docs/derived_collision_tables_all/SAM2_runtime_collision_calls.csv`
- `docs/derived_collision_tables_all/SAM3_runtime_collision_calls.csv`
- `docs/derived_collision_tables_all/runtime_collision_calls.json`
- `openagent/exe_runtime_collision.py`

`openagent/exe_runtime_collision.py` currently provides the resolved body and
foot-solid code sets for the current one-byte mission maps, excluding the first
`CS:2e20` context.  The next deeper step is to preserve per-token relative cell
writes in the runtime, instead of only reducing them to body/foot-solid code
sets and then combining them with the existing visual footprint helper.

## Pass 5 correction: runtime grid axes were transposed

A later pass corrected the axis interpretation used when generating
`openagent/exe_runtime_collision.py`.  The setter multiplies one coordinate by
`0xC8`; because `0xC8 == 25 * 8`, this is the stride between padded X columns,
not a row stride.  Therefore the runtime address is best understood as:

```text
cell = buffer + ((tile_x + 1) * 0xC8) + ((tile_y + 1) << 3)
```

This changes composite-object offsets.  In particular, map byte `0xD2` now has
`foot_solid=1` on the two upper cells `(-1,-1)` and `(0,-1)`, and not on the
lower cells.  See `docs/passes/exe_mechanisms_pass5.md`.
