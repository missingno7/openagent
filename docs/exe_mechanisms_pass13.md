# Pass 13: pickup / score-popup mechanics

This pass follows the real pickup pipeline in the unpacked EXE instead of just
using hand-written score constants.

## Score storage and popup helper

The item interaction dispatcher reads the runtime-cell visual/object id from the
cell record (`+0x1CA`).  For score pickups it:

1. compares that id against constants such as `0x013C`, `0x026A..0x026F`,
   `0x025D`, etc.;
2. adds a constant to `DS:699A/699C`, which is the score accumulator path seen in
   the EXE;
3. clears the picked cell's `+0x1CA` so the object disappears;
4. sets `DS:6832 = -1`, forcing redraw;
5. calls helper `0x55F0` to spawn the floating number sprite.

The helper receives a **one-based** bank-10 tile number.  So:

| Helper arg | Decoded bank 10 tile | Meaning |
|---:|---:|---:|
| `0x11` | `16` | 100 |
| `0x12` | `17` | 250 |
| `0x13` | `18` | 500 |
| `0x14` | `19` | 1000 |
| `0x15` | `20` | 2K |
| `0x16` | `21` | 5K |
| `0x17` | `22` | 10K |

The extracted table is written to
`docs/derived_mechanics/pass13_pickup_mechanics.json`.

## Implemented in runtime

`openagent/semantics.py` now has EXE-derived score values keyed by raw map byte.
`openagent/runtime.py` now spawns a short-lived `ScorePopup` entity when a score
item is collected.  It uses the decoded bank-10 sprites instead of drawing text.

Known raw-code examples from SAM1/SAM2/SAM3:

| Raw code | Runtime visual id | Score | Popup tile |
|---:|---:|---:|---:|
| `0x84` | `0x025D` | 500 | bank 10 tile 18 |
| `0x57` | `0x026A` | 250 | bank 10 tile 17 |
| `0x01` | `0x026B` | 1000 | bank 10 tile 19 |
| `0x5C` | `0x026C` | 500 | bank 10 tile 18 |
| `0x5D` | `0x0275` | 100 | bank 10 tile 16 |
| `0x50` | `0x0130` | 2000 | bank 10 tile 20 |
| `0x8E` | `0x026F` | 10000 | bank 10 tile 22 |

`0x73` is deliberately still ammo, not a score item.  Its branch adds `5` to
`DS:6858`, caps it at `0x63`, clears the runtime cell, plays a pickup sound and
redraws, but does not add to `DS:699A`.

## Notes for the next pass

The same dispatcher contains more non-score pickups and level-state objects:
keys/doors, toggles, teleporter-ish objects, and special flags such as the
previously implemented glasses/hidden-platform mechanic.  These should be
extracted in the same way: compare `+0x1CA` ids, invert them through the runtime
cell table back to raw map bytes, and implement state changes from the branch.
