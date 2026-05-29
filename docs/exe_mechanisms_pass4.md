# EXE mechanisms pass 4: collision aliases and animation state machines

This pass follows two user-observed clues, but does not hard-code them as truth:

- composite crates/platforms appear to have one-way collision only on selected
  runtime cells, not on every visible tile;
- a platform the editor/user calls `D3` behaves like one-way in the original game;
- player/enemy animation needs to come from the EXE control/update code, not from
  arbitrary editor frame cycling.

## 1. Composite collision is asymmetric by runtime-cell write

The EXE-derived writes for raw mission-map byte `0xD2` are:

```text
0xD2:
  dx=-1 dy=-1 visual/c6=0x00BF body=0 foot=1
  dx=-1 dy= 0 visual/c6=0x00C0 body=0 foot=1
  dx= 0 dy=-1 visual/c6=0x00C3 body=0 foot=0
  dx= 0 dy= 0 visual/c6=0x00C4 body=0 foot=0
```

So the engine is not saying "the whole 2x2 object is one-way". It writes
one-way/floor collision only on the left column of that composite object. This
matches the observed shape much better than a visual-footprint heuristic.

The important caveat is that `foot_solid` is a property of the runtime grid cell,
not of a drawn 16x16 sprite. A downward/floor probe later decides whether the
player can stand on the top edge of that cell. Therefore the correct editor
model is:

1. replay EXE map-token writes into the runtime cell grid;
2. run player/actor probes against `+0x1CC` / `+0x1CD`;
3. never infer collision from `TILE_MAP` visual coverage alone.

## 2. The `D3` confusion is probably raw-map byte vs displayed visual tile id

Direct EXE write report:

```text
map byte 0xD3:
  dx=0 dy=0 c6=0x681A c8=0x0000 cA=0xFFFF body=0 foot=0
```

So **raw mission-map byte `0xD3` is not one-way** according to the map loader
writes extracted from SAM1/SAM2/SAM3.

But there is also this write:

```text
map byte 0xD7:
  dx=0 dy=0 c6=0x681A c8=0x02D3 cA=0x0000 body=0 foot=1
```

That means a tile visually identified as sprite/id `0x02D3` is produced by raw
map byte `0xD7`, and that runtime cell is one-way. If the UI labels the rendered
sprite by low byte `D3`, it will look like "D3 is one-way", while the actual map
byte controlling collision is `0xD7`.

A small helper was added so this can be checked explicitly:

```bash
python tools/report_sa_collision_code.py D2 D3 D7
python tools/report_sa_collision_code.py --visual D3
```

Expected key result:

```text
visual low byte 0xD3
  drawn by map byte 0x2A via visual 0x01D3: body=0 foot=0
  drawn by map byte 0xD7 via visual 0x02D3: body=0 foot=1
```

So the next UI/editor task is to distinguish clearly between:

- raw mission-map byte,
- EXE runtime-cell visual ids `c6/c8/cA`,
- rendered atlas bank/tile labels.

## 3. Player animation is state-id driven through `DS:3500`

The keyboard ISR/control code writes player animation state directly. Important
states recovered from SAM1:

| State | Meaning inferred from write sites |
|---:|---|
| `0x01` | right-facing / right-walk base frame |
| `0x05` | left-facing / left-walk base frame |
| `0x09` | right-facing idle/standing |
| `0x0A` | left-facing idle/standing |
| `0x0B` | right-facing alternate/collision state used in checks with `0x01/0x09/0x0D` |
| `0x0D` | right-facing firing/armed overlay state when `DS:6EC1` is set |
| `0x0E` | left-facing firing/armed overlay state when `DS:6EC1` is set |
| `0x0F` | jump/upward frame A |
| `0x10` | jump/upward frame B |

Examples from the EXE:

- pressing left sets `DS:6ECA=1`, `DS:6ECB=0`, and writes `DS:3500=0x05`;
- pressing right sets `DS:6ECB=1`, `DS:6ECA=0`, and writes `DS:3500=0x01`;
- releasing left with no right held writes `0x0A`, otherwise `0x01`;
- releasing right with no left held writes `0x09`, otherwise `0x05`;
- if `DS:6EC1` is set, left/right display states become `0x0E/0x0D`;
- during the upward jump phase, SAM1 `0x1A77..0x1A8C` toggles `DS:3500` between
  `0x0F` and `0x10` every jump tick.

This confirms that the prototype renderer drawing a single fixed player sprite
is not yet faithful. It needs to carry a player animation state and render the
corresponding sprite id/frame selected by the EXE render path.

## 4. Actor/enemy walking animation uses the 0x20-byte actor record

For normal actors/platform-like walkers, the EXE uses the actor slot fields found
in pass 3:

| Field | Role |
|---|---|
| `DS:34D6 + slot*0x20` | frame/counter |
| `DS:34E0 + slot*0x20` | current sprite/object id selected by actor state |
| `DS:34E2 + slot*0x20` | horizontal direction, usually `+1` or `-1` |
| `DS:34E6 + slot*0x20` | movement step/speed |
| `DS:34E8 + slot*0x20` | actor type/state dispatch value |

For the walking collision path, `34D6` is incremented and wrapped:

```text
right/one direction: 0x01..0x13
left/other direction:  0x15..0x27
```

When a side probe hits runtime `+0x1CC`, the code negates `34E2`, then resets the
frame range to the matching direction. This is why enemy/platform walking should
not be implemented as a simple arbitrary two-frame animation detached from the
movement state.

## Generated/updated artifacts

- `tools/extract_sa_animation_mechanics.py`
- `tools/report_sa_collision_code.py`
- `docs/derived_mechanics/animation_mechanics.json`
- `openagent/exe_animation_mechanics.py`
