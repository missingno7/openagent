# OpenAgent Reverse Engineering Status

This is the current handoff document for Secret Agent mechanics.  The pass
documents remain useful as research logs, but this file is the cleaned-up view of
what we should treat as current knowledge.

## Evidence Levels

| Level | Meaning |
| --- | --- |
| Hard fact | Directly observed in original data, unpacked EXE code, generated extractor output, or repeated strings. |
| Derived model | Reconstructed from EXE evidence but still wrapped in Python runtime structure. |
| Prototype fallback | Implemented because it matches play testing or data shape, but the exact original branch is not fully isolated yet. |
| Superseded | A previous assumption kept only in pass logs for audit history. |

When a statement conflicts with an older pass, prefer the newest correction
listed here and in `docs/exe_mechanisms_summary.md`.

## Source Data

Hard facts:

- `SAM?01.GFX` contains 16 banks of 50 masked 16x16 EGA tiles.  The loader path
  is proven by `secret_agent_editor`.
- `SAM?02.GFX` contains three banks of 50 masked 8x8 sprites.
- `SAM?03.GFX` is an encrypted level archive with 17 blocks per episode.  Block
  0 is the top-down island map, blocks 1..16 are side-view mission levels.
- Every level block is 2016 bytes: 48 rows by 42 bytes.  A row beginning with
  `*` maps onto the previous visual row as an overlay row.
- The three episodes use the same broad formats and very similar executable
  mechanisms.  Address offsets can differ, but the recovered tables and token
  semantics are shared enough for one aggregate runtime.

## World Map Mode

Hard facts:

- Level index 0 is not a platform level.  It is the island/world map.
- The player marker is raw `0x59`, rendered from bank 13 tile 0.
- Entrance candidates are raw `0x4D`, `0x4F`, and `0x50`.  Counting those in
  row-major order gives exactly 16 entrances per episode.
- World-map raw bytes use a different meaning table from mission bytes.  For
  example world raw `0x62` is coastline, while mission raw `0x62` is the moving
  platform.

Current model:

- Grass/path codes are passable.  Tree/forest, water and coastline codes block
  world-map movement.
- Entrance order is data-derived but the original EXE entrance mapping and
  world-map collision routine still need a dedicated pass.

## Mission Runtime Cells And Collision

Hard facts:

- Mission collision is not derived from visible atlas footprint and not from
  "BG vs FG" layer names.
- The EXE token parser calls a runtime-cell setter at SAM1 `0x1059e` and
  SAM2/SAM3 `0x1062e`.
- The runtime buffer is column-major after the pass 5 correction:

```text
cell = buffer + ((tile_x + 1) * 0xC8) + ((tile_y + 1) << 3)
```

- `0xC8` is the stride between padded X columns: 25 padded Y cells times 8
  bytes per runtime cell.
- Recovered cell fields:

| Offset | Meaning |
| --- | --- |
| `+0x1C6` | first internal draw/code word |
| `+0x1C8` | second internal draw/code word |
| `+0x1CA` | third internal draw/code word, used heavily by interaction/pickup logic |
| `+0x1CC` | body/wall collision byte |
| `+0x1CD` | floor/one-way collision byte |

- Setter argument `bp+6 == 0` writes the full cell record including collision.
- Setter argument `bp+6 != 0` writes only `+0x1CA` and redraws.  Collision is
  not changed.
- The SAMLEV row marker feeds that argument, so `*` overlay rows can affect
  visuals/interactions but do not directly create body/floor collision.
- `openagent/exe_runtime_collision.py` is generated from included mission parser
  contexts only: `CS:3a59..3a8f` and `CS:66f9..68a7`.  The older
  `CS:2e20..2e86` context is excluded because it gives wrong answers for current
  one-byte mission bytes such as `0x70`.

Important collision examples:

| Raw code | Current conclusion |
| --- | --- |
| `0x18` | passable |
| `0x70` | passable in the current mission map table |
| `0xEA`, `0xEB`, `0xEC` | passable overlay/object writes |
| `0xD2` | 2x2 composite with foot-solid on the two upper cells only |
| `0xD3` | raw byte itself is not the one-way platform |
| `0xD7` | emits visual id `0x02D3` and has foot-solid one-way behavior |

Player collision model:

- The player sprite is drawn as 16x16, but collision probes are narrower:
  `x+3`, `x+12`, `y`, and `y+15`.
- Body probes use `+0x1CC`; floor/one-way probes use `+0x1CD`.
- Exact death/lives/checkpoint handling is still open.

## Player State And Motion

Hard facts:

- Player position/state is stored separately from actor slots:

| Address | Meaning |
| --- | --- |
| `DS:34EE` | player X |
| `DS:34F0` | player Y |
| `DS:34F2` | previous player X |
| `DS:34F4` | previous player Y |
| `DS:3500` | player animation/state id |

- Horizontal movement is tick based and uses integer pixel steps selected by
  the EXE path around `0x532D`.
- Jump/fall is table driven, not a continuous gravity integration.
- The corrected vertical table is shared by jump ascent and fall:

```text
index:  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19
value:  8  8  8  4  4  2  2  2  1  1  2  2  2  4  4  8  8  8  8
```

- `BC0E` starts a jump by setting `DS:6EC1 = 1` and `DS:34EA = 0`.
- While `DS:6EC1` is set, the update increments `34EA` and moves upward by the
  table value.  At `34EA == 0x0A`, it clears the jump flag and fall continues
  from the same counter.
- Player draw state comes from `DS:3500` plus `DS:34F6 / 5` for walking states.

Important state/frame notes:

- `DS:3500 = 0x01/0x05` are right/left walking bases.
- `DS:3500 = 0x09/0x0A` are right/left idle.
- `DS:3500 = 0x0B/0x0C` render shoot right/left as decoded bank 13 tiles 10/11.
- Jump-looking frames are decoded bank 13 tiles 12/13.

## Actors And Dynamic Objects

Hard facts:

- Runtime actors are 0x20-byte slots.  The dispatcher addresses them as
  `slot << 5`.
- Important actor fields:

| Field | Meaning |
| --- | --- |
| `DS:34CE + slot*0x20` | actor X |
| `DS:34D0 + slot*0x20` | actor Y |
| `DS:34D2/+34D4` | previous X/Y |
| `DS:34D6` | animation/frame counter |
| `DS:34D8` | timer period for some states |
| `DS:34DA` | timer/aux counter |
| `DS:34E0` | current object/sprite id |
| `DS:34E2` | horizontal direction |
| `DS:34E4` | vertical direction |
| `DS:34E6` | per-DOS-tick pixel step |
| `DS:34E8` | behavior/state dispatch value |
| `DS:34EA` | skip/inactive flag in some paths |

- Actor updates are paced on the DOS tick clock, not modern render frames.
- Actor movement and collision should query the runtime cell grid, not raw map
  bytes or rendered pixels.

Known actor/object families:

| Raw code | Status |
| --- | --- |
| `0x23` | rotating satellite, bank 10 tiles 0..3, 3 DOS ticks per phase after pass 24 |
| `0x38`, `0x39`, `0x30`, `0x67`, `0x47` | bank-14 guard family with EXE-derived object ids, speeds, shooting timers and hit degradation |
| `0x3B`, `0x3E` | timed bank-3 beam traps |
| `0x3F`, `0x41` | retracting floor/ceiling spike traps |
| `0x51`, `0x52`, `0x3C`, `0x3D` | stationary shooter traps, indestructible actor objects |
| `0x56`, `0x58`, `0x63`, `0x24`, `0xAE` | special/multi-tile actors from the extracted table |
| `0x5F` | shark swimmer, bank 4 directional tiles 44..47 |
| `0x62` | moving platform, starts left, currently 2 px per DOS tick |
| `0x65` | special moving enemy, state `0x22`, speed 2 px per DOS tick in the special actor table |
| `0x6E`, `0x7F` | special moving actors with table-derived state/speed |
| `0xA7` | pushable barrel with special overlap/anti-stick handling |

Prototype fallbacks:

- Some actor state branches are represented by the right object id, speed and
  viewport gate, but still need exact per-state collision/damage side effects.
- The `0x62` moving-platform branch has not been fully isolated, but its current
  direction/tick-step model is closer than the original px/sec fallback.

## Pickups, Inventory And Doors

Hard facts:

- Pickup/interaction code compares runtime cell `+0x1CA`, not just the raw map
  byte.
- Score is accumulated through `DS:699A/699C`.
- Pickup removal clears `+0x1CA`, forces redraw via `DS:6832 = -1`, and spawns a
  floating score helper.
- Score popup helper arguments are one-based bank 10 tiles:

| Popup | Decoded bank 10 tile |
| --- | --- |
| 100 | 16 |
| 250 | 17 |
| 500 | 18 |
| 1000 | 19 |
| 2K | 20 |
| 5K | 21 |
| 10K | 22 |

Known raw examples:

| Raw code | Meaning |
| --- | --- |
| `0x5B` | money bag score pickup |
| `0x84` | 500 point score pickup |
| `0x73` | ammo: adds 5 shots, capped at 99, no score |
| `0x72` | reveal glasses, affects hidden platform visibility |
| `0x2B -> 0x2C` | green key/door |
| `0x2D -> 0x2E` | red key/door |
| `0x2F -> 0x34` | blue key/door |

Open work:

- Finish all key/door/toggle/teleporter/exit interaction branches from the same
  `+0x1CA` dispatcher rather than relying on code names.

## Rendering And Animation

Hard facts:

- `0x35`, `0x36`, and `0x37` are static variants of the active level background,
  not time-varying animation frames.
- The confirmed simple animated tile case is raw `0x60`, runtime visual id
  `0x01F3`, decoded as bank 4 tile 48 alternating with bank 4 tile 0.
- Dynamic actors must be skipped from the static level bitmap and drawn from
  their runtime state.
- Removed pickups/opened doors are runtime cell-state changes, not source-level
  mutations of `SAM?03.GFX`.
- Mission base draw order from the EXE is: static non-object cell redraw,
  player, static `+0x1CA` object/foreground redraw, then actor slots from index
  2 upward.
- Static runtime cell words `+0x1C6` and `+0x1C8` are the base/background parts.
  The separate far-call target `d93:2530` (linear `0xFE60`) reads only
  `+0x1CA` and redraws it as the static object/foreground pass.
- Source FG/BG does not decide player occlusion.  Normal BG codes can render in
  front when their EXE-derived write has nonzero `cA`; raw `0xEB` is the current
  anchor example (`cA=0x02FC`).
- `*` rows use the setter's nonzero-marker branch at `0x1059E`: they write only
  the `+0x1CA` overlay visual word and skip collision-byte writes.

## Superseded Assumptions

Do not reintroduce these:

- "World map is just platform level 0."  It is a separate top-down mode.
- "Non-empty code means solid."  Collision comes from EXE runtime cell writes.
- "BG/FG decides collision or draw order in a simple engine-layer sense."  The
  real static foreground rule is the hardcoded `+0x1CA` object redraw path; `*`
  rows only feed that path through the setter's overlay branch.
- "Use `TILE_MAP` visual footprint for collision."  Composite collision is
  emitted by parser setter calls and can differ from the rendered footprint.
- "Raw `0x70` is foot-solid in current mission maps."  That was from the wrong
  parser context.
- "Runtime grid is row-major with `0xC8` as Y stride."  Pass 5 corrected it to
  X-column stride.
- "`0x35..0x37` are animated tiles."  They are static background variants.
- "Every actor object can be shot."  The hit dispatcher branches by object id;
  stationary shooter traps are indestructible in the decoded paths.

## Highest-Value Open Questions

1. Original world-map collision and entrance-to-level mapping.
2. Full `+0x1CA` interaction dispatcher: doors, exits, teleporters, toggles and
   special pickups.
3. Exact remaining actor state branches for non-guard enemies and special traps.
4. Remaining object-specific projectile hit branches beyond the known
   object-id damage and indestructible actor filters.
5. Runtime-cell visual renderer based on generated `c6/c8/cA` writes instead of
   editor `TILE_MAP` draw refs.
6. Player damage, lives, death, respawn and episode progression.
7. Remaining sound ID names and exact `0x287e` priority/preemption semantics.
