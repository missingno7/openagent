# Pass 18: actor spawn table and guard speeds

This pass replaces the hand-guessed bank-14 guard speed table with values
extracted from the SAM special actor token table at `CS:3A59`.

## Extracted fields

The parser routine for the `CS:3A59` token table allocates a 0x20-byte actor slot
and writes these fields:

```text
DS:34E0 + slot*0x20 = object/sprite id
DS:34E2 + slot*0x20 = initial horizontal direction
DS:34D6 + slot*0x20 = animation frame counter
DS:34E6 + slot*0x20 = per-DOS-tick pixel step
DS:34D8 + slot*0x20 = timer period for some behaviours
DS:34DA + slot*0x20 = timer counter
DS:34E8 + slot*0x20 = behaviour state
```

For the bank-14 guard family the EXE writes:

| raw code | bank 14 base | object id | state `34E8` | speed `34E6` | shoot timer |
|---:|---:|---:|---:|---:|---:|
| `0x38` | 0  | `0x015F` | `1` | `1 px/tick` | — |
| `0x39` | 8  | `0x0167` | `2` | `1 px/tick` | — |
| `0x30` | 16 | `0x016F` | `3` | `2 px/tick` | — |
| `0x67` | 24 | `0x0177` | `4` | `2 px/tick` | `random(0x32)+0x32`, i.e. 50–99 ticks |
| `0x47` | 32 | `0x017F` | `5` | `2 px/tick` | `random(0x14)+0x1E`, i.e. 30–49 ticks |

So the stronger guards are actually faster, not just tougher/shooting.  This is
now reflected in `openagent/exe_actor_mechanics.py` and `openagent/entities.py`.

The same actor init path also calls `random(2)` when setting `34E2`, so the
initial left/right facing of these actors is not a fixed raw-code property.  The
runtime uses a deterministic hash of `(raw code, x, y)` as a reproducible stand-in
for that EXE RNG.

## Other actor-table notes

The same extraction pass also confirms:

- raw `0x65` is a special actor with `34E6 = 2` and behaviour state `0x22`;
- raw `0x6E` is also `34E6 = 2` and has a timer `random(0x14)+0x1E`;
- raw `0x75` and `0x76` initialise `34E6` to zero, so their full motion is likely
  driven by their behaviour states rather than by the simple horizontal walker
  path.  OpenAgent keeps a conservative fallback for those until their dispatch
  routines are decoded.

Generated data: `docs/derived_mechanics/pass18_special_actor_table.json`.
