# EXE-derived Secret Agent collision table

Status: superseded first-pass extraction.  Keep this file as historical
evidence, but do not use it as the current mission collision source.  The newer
pipeline is `docs/runtime_collision_table_research.md`,
`docs/exe_runtime_mechanisms_pass2.md`, `docs/exe_mechanisms_pass5.md`, and the
generated `openagent/exe_runtime_collision.py`.

Most importantly, this first pass did not include the later mission parser
contexts and therefore gave the wrong current conclusion for bytes such as
`0x70`.

This table is extracted from the map-token routine in the unpacked DOS executables, not from visual heuristics. The extractor is `tools/extract_sa_collision_table.py`.

## What the routine does

- The loader compares a two-byte SAMLEV token such as `01 70` against an embedded token table.
- On match it calls the runtime-cell setter, which writes three internal draw/code words and two collision bytes into the padded level buffer.
- The relevant runtime fields are the same ones previously identified: code words at `+0x1c6/+0x1c8/+0x1ca`, body collision at `+0x1cc`, and floor/one-way collision at `+0x1cd`.
- `SAM1`, `SAM2`, and `SAM3` all contain 59 entries. The collision bits match; some variable addresses differ (`word_681a` versus `word_6840`) because episode binaries have different globals.

## Important findings

- `01 70` (`\x01p`) is **body-passable but foot-solid**: this is a one-way/floor-channel object, not a normal wall.
- The one-way group is `01 6f`, `01 70`, `01 71`, `01 72` (`o/p/q/r`): all have `body_solid=0`, `foot_solid=1`.
- Tokens `01 42`..`01 47`, `01 55`, `01 61`, `01 66`, `01 67`, and one part of `01 77` set `body_solid=1`.
- Composite objects are real at the runtime-cell level: token `01 77` writes two cells, one at `x-1` with body collision and another at `x` with different layer data. This confirms that composite collision cannot be inferred from the anchor tile alone.

## Full SAM1 table

| token | internal_code | layer_b | layer_c | body | foot | target |
|---|---:|---:|---:|---:|---:|---|
| `01 41` \x01A | `0x01F5` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 42` \x01B | `0x01F6` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 43` \x01C | `0x01F7` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 44` \x01D | `0x01F8` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 45` \x01E | `0x01F9` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 46` \x01F | `0x01FA` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 47` \x01G | `0x01FB` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 48` \x01H | `word_681a` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 49` \x01I | `word_681a` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 4a` \x01J | `0x0295` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 4b` \x01K | `word_681a` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 4c` \x01L | `word_681a` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 4d` \x01M | `?` | `0x00` | `0x0205` | 0 | 0 | x,y |
| `01 4d` \x01M | `?` | `0x00` | `0x0201` | 0 | 0 | x,y |
| `01 4e` \x01N | `?` | `0x00` | `0x0206` | 0 | 0 | x,y |
| `01 4e` \x01N | `?` | `0x00` | `0x0202` | 0 | 0 | x,y |
| `01 4f` \x01O | `?` | `0x00` | `0x0207` | 0 | 0 | x,y |
| `01 4f` \x01O | `?` | `0x00` | `0x0203` | 0 | 0 | x,y |
| `01 50` \x01P | `?` | `0x00` | `0x0208` | 0 | 0 | x,y |
| `01 50` \x01P | `?` | `0x00` | `0x0204` | 0 | 0 | x,y |
| `01 51` \x01Q | `0x0205` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 52` \x01R | `0x0206` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 53` \x01S | `0x0207` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 54` \x01T | `0x0208` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 55` \x01U | `0x0209` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 56` \x01V | `0x020A` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 57` \x01W | `0x020B` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 58` \x01X | `0x020C` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 30` \x010 | `0x020D` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 5a` \x01Z | `0x020E` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 61` \x01a | `0x020F` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 62` \x01b | `0x0210` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 63` \x01c | `0x0211` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 64` \x01d | `0x0212` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 65` \x01e | `0x0213` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 66` \x01f | `0x0214` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 67` \x01g | `0x0215` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 68` \x01h | `0x0216` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 69` \x01i | `0x0217` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 6a` \x01j | `0x0218` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 6b` \x01k | `0x0219` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 6c` \x01l | `0x01FC` | `0x00` | `0x00` | 1 | 0 | x,y |
| `01 6c` \x01l | `word_681a` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 6d` \x01m | `word_681a` | `0x00` | `0x0299` | 0 | 0 | x,y |
| `01 6e` \x01n | `word_681a` | `0x00` | `0x029A` | 0 | 0 | x,y |
| `01 6f` \x01o | `word_681a` | `0x029F` | `0x00` | 0 | 1 | x,y |
| `01 70` \x01p | `word_681a` | `0x02A0` | `0x00` | 0 | 1 | x,y |
| `01 71` \x01q | `word_681a` | `0x02A1` | `0x00` | 0 | 1 | x,y |
| `01 72` \x01r | `word_681a` | `0x02A2` | `0x00` | 0 | 1 | x,y |
| `01 73` \x01s | `0x02AB` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 74` \x01t | `word_681a` | `0x00` | `0x02AC` | 0 | 0 | x,y |
| `01 75` \x01u | `word_681a` | `0x00` | `0x02AD` | 0 | 0 | x,y |
| `01 76` \x01v | `word_681a` | `0x00` | `0x02AE` | 0 | 0 | x,y |
| `01 78` \x01x | `word_681a` | `0x00` | `0x02B0` | 0 | 0 | x,y |
| `01 79` \x01y | `word_681a` | `0x00` | `0x02B1` | 0 | 0 | x,y |
| `01 7a` \x01z | `0x02B2` | `0x00` | `0x00` | 0 | 0 | x,y |
| `01 77` \x01w | `word_681a` | `0x00` | `0x02AF` | 0 | 0 | x,y |
| `01 77` \x01w | `0x02` | `0x00` | `0xB3` | 1 | 0 | x-1,y |
| `01 77` \x01w | `0x02` | `0x00` | `0xB7` | 0 | 0 | x,y |
