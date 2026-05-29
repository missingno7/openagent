# EXE runtime mechanisms pass 2

Status note: the setter branch findings in this file are still current, but the
cell address formula shown below was corrected in pass 5.  Use the column-major
formula from `docs/exe_mechanisms_pass5.md` and
`docs/reverse_engineering_status.md`:

```text
cell = buffer + ((tile_x + 1) * 0xC8) + ((tile_y + 1) << 3)
```

This pass continues from `runtime_collision_table_research.md` and replaces the
last visual-footprint collision approximation with an EXE-style runtime-cell
replay.

## Runtime cell setter

The shared map-token setter is at:

| Episode | Setter address |
| --- | ---: |
| SAM1 | `0x1059e` |
| SAM2 | `0x1062e` |
| SAM3 | `0x1062e` |

The setter computes the runtime cell address as:

```text
cell = runtime_base + (y + 1) * 0xC8 + (x + 1) * 8
```

So every logical cell record is 8 bytes wide and each row is `0xC8` bytes.  The
stored gameplay fields are:

| Runtime offset | Meaning recovered from reads/writes |
| --- | --- |
| `+0x1C6` | first internal draw/code word |
| `+0x1C8` | second internal draw/code word |
| `+0x1CA` | third internal draw/code word / overlay word |
| `+0x1CC` | normal body/wall collision byte |
| `+0x1CD` | foot/floor collision byte |

The important extra discovery is that the setter has two branches:

- if argument `bp+6 == 0`: write the full runtime cell record, including
  `+0x1CC/+0x1CD` collision flags;
- if argument `bp+6 != 0`: write only `+0x1CA` and redraw; collision flags are
  not changed.

That last argument is passed from the row marker in the main SAMLEV row parser.
Rows whose first byte is `'*'` are therefore foreground/overlay rows: they can
change rendering, but they do not directly create wall/floor collision.  The
prototype used to collide against both visual layers, which was wrong.

## Parser contexts kept vs excluded

The generated module now keeps only parser contexts that correspond to actual
`SAM?03.GFX` mission map bytes:

| EXE token table | Included? | Reason |
| --- | --- | --- |
| `CS:2e20..2e86` | no | different ASCII-like parser context; it gives wrong answers for mission bytes such as `0x70` |
| `CS:3a59..3a8f` | yes | special low-byte object parser, includes codes such as `0x5B`, `0xAE`, `0xD4` |
| `CS:66f9..68a7` | yes | main SAMLEV one-byte mission row parser |

The new generator is `tools/generate_sa_runtime_collision_module.py`.  It reads
`docs/derived_collision_tables_all/SAM1_runtime_collision_calls.json` and creates
`openagent/exe_runtime_collision.py` with exact per-token relative writes.

## Composite objects

`openagent/exe_runtime_collision.py` now exposes `RUNTIME_CELL_WRITES`, not only
coarse `BODY_SOLID_CODES` / `FOOT_SOLID_CODES` sets.  This matters because a map
code can write multiple runtime cells at positions relative to its anchor.

Examples from the EXE-derived table:

```text
0x70 -> (dx=0, dy=-1) passable, (dx=0, dy=0) passable
0x18 -> (dx=0, dy=0) passable
0xEA/0xEB/0xEC -> (dx=0, dy=0) passable overlay words
0x77 -> (dx=-1, dy=0) body-solid, (dx=0, dy=0) passable
0xD2 -> four cells:
        (dx=-1, dy=-1) foot-solid
        (dx=-1, dy= 0) foot-solid
        (dx= 0, dy=-1) passable
        (dx= 0, dy= 0) passable
```

This confirms that collision is not attached to the visible `TILE_MAP` footprint
and not even always attached to the anchor cell.  It is attached to the runtime
cell writes emitted by the EXE token parser.

## Runtime integration

`openagent.level_model.build_runtime_collision_grid()` now replays these writes
for a level.  It applies them in map order, so later full cell writes override
earlier collision flags at the same runtime cell, matching the setter behavior.

`openagent.runtime` now asks this reconstructed runtime grid for body/floor
blocking.  The old `visual_coverage_cells()` path is no longer used for
collision.

Open questions for the next pass:

- recover the exact actor/player update routines that consume `+0x1CC/+0x1CD`
  for every actor mode, not just the simplified player runtime;
- recover jump/gravity constants from the actor state machine instead of tuning
  `JUMP_SPEED`/`GRAVITY` by feel;
- identify which map codes trigger inventory, score, doors, scripted pickups and
  level exits by following writes around the actor/object interaction routines.
