# EXE mechanisms pass 132 — cleanup, rocket animation, and raw 0x75 state 0x23 correction

## Scope

- Remove stale/unused Python wiring left by earlier stationary-launcher passes.
- Animate stationary launcher rockets from raw `0x3C/0x3D` with the decoded bank-4 rocket frames.
- Re-audit raw `0x75` / object `0x006D` / state `0x23` against ASM instead of treating it as a normal walking contact bomb.

## ASM evidence

### Stationary rocket launchers

The stationary launcher branch at `SAM1:0x6B74..0x6D47` still owns the raw `0x51/0x52/0x3C/0x3D` family.

Confirmed in earlier pass 129 and preserved here:

- raw `0x3C` / state `0x0C` calls helper `0x5784` with `x = actor_x + 16`, `y = actor_y`, `direction = +1`, `speed = 4`, object `0x01E8`;
- raw `0x3D` / state `0x0D` calls helper `0x5784` with `x = actor_x - 16`, `y = actor_y`, `direction = -1`, `speed = 4`, object `0x01EC`;
- projectile state `0x0E` calls helper `0x53C4` for player contact and does not consume the projectile there; helper `0x547C` owns impact/consumption.

The decoded atlas shows the rocket animation frames in bank 4:

- right-moving rocket: tiles `37, 38, 39`;
- left-moving rocket: tiles `41, 42, 43`.

Python now stores those frame triples in `Projectile.anim_tiles` for `0x3C/0x3D` shots while keeping the existing tile-right/tile-left fallback fields for non-animated code paths.

### Raw `0x75` / state `0x23`

The raw `0x75` initializer at `SAM1:0x127C6..0x1288C` writes an actor slot, not a normal patrol enemy:

```asm
127c6: movw $0x006d, 0x34e0(%di) ; object id
12824: movw $0x0001, 0x34e2(%di) ; direction +1
12832: xor  %ax,%ax
12834: mov  %ax,0x34e4(%di)      ; y direction 0
12840: movw $0x0001, 0x34d6(%di) ; frame counter
12850: mov  %ax,0x34e6(%di)      ; speed 0
1285e: mov  %ax,0x34d8(%di)
1286c: mov  %ax,0x34da(%di)
12878: movw $0x0003, 0x34dc(%di) ; hit counter
12886: movw $0x0023, 0x34e8(%di) ; state 0x23
```

The update branch at `SAM1:0x9FED..0xA15E`:

- increments `DS:34D6` and wraps it back to `1` after `0x13`;
- commits the precomputed candidate X back into `DS:34CE`; because `DS:34E6=0`, this does not make the actor patrol;
- calls helper `0x53C4` with `(actor_x, actor_y)` for player-contact damage;
- calls helper `0x547C` with the same coordinate for projectile/actor impact;
- only when `0x547C` reports a hit does it set `DS:34CC=3` and decrement `DS:34DC`;
- after `DS:34DC` reaches zero it plays sound `0x13`, awards `+1000`, rewrites the actor to object `0x00AA/state 0x1389`, aligns X with `(x+8)&0xfff0`, and runs the side-effect draw/shrapnel path.

## Python changes

- `SPECIAL_ACTOR_MODELS[0x75]` is now `step_px=0`, `random_initial_direction=False`, `object_id=0x006D`, `behavior_state=0x23`, `aux_dc=3`.
- Object `0x006D` is now shootable with three hits, matching `DS:34DC=3`.
- `update_entities_tick()` now has a dedicated `state23_contact_bomb` branch:
  - advances only `frame_counter` `1..0x13`,
  - applies `0x53C4`-style player contact damage,
  - never walks,
  - never decrements its hit counter from player contact.
- `hit_enemy_with_projectile()` now models the `0x547C` path for this actor:
  - non-final hits decrement HP and set the 3-tick hit flash,
  - the final hit calls the existing `explode_contact_bomb()` score/shrapnel effect.
- Rendering uses `state23_contact_bomb_tile()` so raw `0x75` stays in bank2 tiles `8..11`; it no longer flips into the generic left-facing `12..15` family.
- Removed an unused `STATIONARY_SHOOTER_PROJECTILE` unpack in `extract_level_entities()`.

## Tests

Added `tools/check_state23_contact_bomb_accuracy.py` and extended `tools/check_stationary_shooter_accuracy.py`.

The handoff now runs:

```bash
python tools/check_stationary_shooter_accuracy.py
python tools/check_state23_contact_bomb_accuracy.py
python tools/check_handoff.py
```

Result: `Handoff checks OK`.

## Remaining gaps

- Exact helper `0x547C` side effects beyond this actor family are still partial.
- The object `0x00AA/state 0x1389` destructive follow-up is represented by the existing explosion/shrapnel approximation rather than by a full draw/clear reconstruction.
- A full enemy body-contact allowlist should still replace the current piecemeal contact-policy checks.
