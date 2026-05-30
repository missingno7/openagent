# EXE mechanisms pass 3: player/actor movement and jump model

This pass continues the rule: do not decide Secret Agent gameplay from visual
appearance or user hints.  Extract the mechanism from the unpacked EXE first,
then use hints only as sanity checks.

## 1. Actor/object records are 0x20-byte structs

The update dispatcher around SAM1 `0x816b..0x82d5` iterates slots starting at
actor index `2`.  Every slot is addressed as `slot << 5`, so each runtime actor
record is `0x20` bytes.

Recovered high-confidence fields:

| Field | Meaning |
|---|---|
| `DS:34ce + slot*0x20` | X position in pixels |
| `DS:34d0 + slot*0x20` | Y position in pixels |
| `DS:34d2 + slot*0x20` | previous X |
| `DS:34d4 + slot*0x20` | previous Y |
| `DS:34d6 + slot*0x20` | animation/collision counter |
| `DS:34da + slot*0x20` | timer/aux counter in some states |
| `DS:34e0 + slot*0x20` | sprite/object id written during state changes |
| `DS:34e2 + slot*0x20` | horizontal direction, usually `+1` or `-1` |
| `DS:34e4 + slot*0x20` | vertical direction, usually `+1` or `-1` |
| `DS:34e6 + slot*0x20` | step speed used by the dispatcher |
| `DS:34e8 + slot*0x20` | actor type/state dispatch value |
| `DS:34ea + slot*0x20` | skip/inactive flag checked before dispatch |

The dispatcher computes candidate movement from `direction * speed`, stores old
position into `34d2/34d4`, and calls the collision-state routine at `0x5a37` for
states below `0x1e`.

## 2. Actor collision routine confirms the runtime-grid model

SAM1 routine `0x5a37` is an actor collision routine.  It does **not** look at raw
map bytes.  It indexes the runtime collision buffer and tests the same bytes we
previously recovered from the map loader:

```text
runtime cell byte +0x1cc = normal/body collision
runtime cell byte +0x1cd = floor / one-way / vertical channel
```

The probe geometry in that actor routine is:

```text
tile_x_left   = (x >> 4) + 1
tile_x_right  = tile_x_left + 1
tile_y_top    = (y >> 4) + 1
tile_y_bottom = ((y + 15) >> 4) + 1
cell_offset   = tile_y * 0xC8 + (tile_x << 3)
```

When a horizontal side is blocked, the routine flips `34e2` between `+1` and
`-1` and resets/loops `34d6` between the `0x01..0x13` and `0x15..0x27` animation
ranges.  That means the moving-platform/enemy prototype should not be driven by
arbitrary pixel speeds forever; the EXE uses slot state, direction, speed and
collision counters.

## 3. Player globals are separate from actor slots

Player position is not one of the normal actor slots:

| Address | Meaning |
|---|---|
| `DS:34ee` | player X |
| `DS:34f0` | player Y |
| `DS:34f2` | previous player X |
| `DS:34f4` | previous player Y |
| `DS:3500` | player animation/state id |

This is why the runtime has to treat the player separately while still using the
same runtime cell buffer for environment collision.

## 4. Keyboard/control flags recovered

The keyboard ISR starts at SAM1 `0x0000`; it reads scan code `in al, 0x60` and
stores it at `DS:6824`.  It then compares against configurable scan-code words:

| Address | Role |
|---|---|
| `DS:70be` | left key |
| `DS:70c0` | right key |
| `DS:70c2` | fire/action key used for projectile spawn path |
| `DS:70ba` | up / ladder-ish key |
| `DS:70bc` | down / ladder-ish key |
| `DS:70c4` | fire/extra action held flag path |

The ISR writes held/edge flags:

| Address | Meaning |
|---|---|
| `DS:6eca` | left held |
| `DS:6ecb` | right held |
| `DS:6ec3` | up/ladder-ish held |
| `DS:6ec4` | down/ladder-ish held |
| `DS:6ecd` | fire/action held |
| `DS:6ec2` | movement/control edge flag cleared by some movement paths |

Animation state `DS:3500` is updated here too.  Example values seen directly in
this pass: `0x01`, `0x05`, `0x09`, `0x0a`, `0x0b`, `0x0c`, `0x0d`, `0x0e`.

## 5. Jump height: not a continuous gravity constant

The important finding for your “jump height nesedí” observation is that the EXE
upward phase is table-driven.

Routine around SAM1 `0x53c4..0x5479` can start a jump/bounce/knockback-like
state by setting:

```text
DS:69f5 = 1
DS:69f6 = 0x23    ; 35 ticks
```

Then SAM1 `0x1a6b..0x1ae8` performs the upward motion:

```text
previous_x = player_x
previous_y = player_y
animation_state toggles 0x0f / 0x10
--DS:69f6
di = DS:69f6 << 1
step = word ptr [DS:69f6 + di]
player_y -= step
```

So the current `runtime.py` constants (`JUMP_SPEED`, `GRAVITY`, `MAX_FALL`) are a
prototype approximation only.  They should eventually be replaced with a
recovered 35-tick displacement table plus the corresponding falling path.

Open issue: the displacement table is referenced in the runtime DS image; the
current extractor identifies the access pattern and addresses, but does not yet
recover the table values.  The next pass should trace where the DS runtime image
is initialised/copied after LZEXE unpacking, or recover it by DOSBox memory dump.

## Generated artifacts

- `tools/extract_sa_player_mechanics.py`
- `docs/derived_mechanics/player_mechanics.json`
- `openagent/exe_player_mechanics.py`
