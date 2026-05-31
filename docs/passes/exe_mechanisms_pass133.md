# Pass 133 — moving-platform jump carry must honor DS:6EC1

## Trigger

After pass 131 fixed the normal jump/fall table, playtesting exposed a new
moving-platform regression: when the player jumped while riding a moving
platform, he could remain at the platform height in the air/jump animation,
continue moving horizontally, and only fall again after an unrelated damage
state.

## Cause in Python

The platform actor branch in Python snapped/carried the player whenever the
narrow platform top rectangle matched, even if the normal jump flag was active.
That meant that on every actor tick during a jump:

1. `update_entities_tick()` snapped `player.y = platform.y - 16`;
2. the carry side effect reset `player.fall_ticks` to
   `PLAYER_VERTICAL_COUNTER_INITIAL`;
3. `update_player_tick()` then saw `jump_anim_timer > 0`, advanced the jump
   counter from the reset high value, and produced a `0 px` jump step while
   keeping the air pose active.

The result was a self-sustaining levitation state.

## ASM evidence

The moving-platform carry branch is around `SAM1:0x7FA6..0x8105`.  Pass 106
already noted that it has no `DS:69F5` hard-death guard, which is why a death
sprite can still be caught by a moving platform.  The same branch also contains
a separate normal-jump guard:

```asm
801f: cmp byte [DS:6EC1],0
8024: je  8029       ; only carry when the normal jump flag is clear
8026: jmp 8105       ; jump active: skip player snap/carry
8030: actor_y - 0x10 -> DS:34F0
803a: DS:6EC1 = 0
8073..80a3: carry DS:34EE by actor speed
8105..8165: platform actor still moves itself
```

So the correct split is:

- `DS:69F5` hard death does **not** block platform catch/carry;
- `DS:6EC1` normal jump **does** block platform catch/carry.

Python mirrors `DS:6EC1` with `Player.jump_anim_timer`.

## Runtime changes

- `platform_carry_contact_asm()` now returns `False` while
  `player.jump_anim_timer > 0`.
- The platform actor still moves normally while the player is jumping; only the
  player snap/carry/fall-counter reset is skipped.
- `tools/check_death_camera_platform.py` now has a jumping-player regression
  that verifies the platform moves but the player is not carried or reset.

## Files touched

- `openagent/movement_collision.py`
- `tools/check_death_camera_platform.py`
- `dissassembly/annotated/SAM1_tick_accuracy_excerpts.asm`
- `docs/registry/mechanics_status.json`
- `docs/registry/tick_accuracy_ledger.json`
- `docs/ASM_EVIDENCE_INDEX.md`
- `docs/TICK_ACCURACY_LEDGER.md`
- `docs/MECHANICS_INDEX.md`
- `docs/PASS_INDEX.md`

## Validation

```bash
python tools/check_death_camera_platform.py
python tools/check_handoff.py
```

