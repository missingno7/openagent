# EXE mechanisms pass 121 — stationary launcher contact fallback + barrel hypothesis discipline

## Scope

User gameplay notes are treated as hypotheses, not sources of truth.  This pass
rechecked two areas that were still suspicious after pass 120:

1. raw `0x51` / `0x52` stationary launcher touch damage, and
2. raw `0xA7` barrel release / pushed-off-edge fall claims.

## Raw `0x51` / `0x52`: remaining body-touch damage path

Pass 120 corrected the dynamic body helpers:

- `actor_is_indestructible_solid()` no longer treats `stationary_shooter` as a
  player blocker,
- `actor_is_contact_hazard()` no longer treats it as a contact hazard.

That was not enough.  `OpenAgentApp.check_enemy_touch()` still had an older broad
fallback that damaged the player for most `entities.enemies` entries.  Since raw
`0x52` / `0x51` are represented as `kind="stationary_shooter"`, overlapping the
launcher body could still call `hurt_player()` even though the explicit helper
policy said otherwise.

### Evidence used

- `SAM1:0x6B74..0x6D47` implements the right/left stationary launcher states
  `0x0A` / `0x0B`.
- `SAM1:0x6C0D..0x6C2D` spawns raw `0x52` projectile object `0x01D6` via helper
  `0x5784`.
- `SAM1:0x6CF8..0x6D18` spawns raw `0x51` projectile object `0x01D6` via helper
  `0x5784`.
- The older decoded hit-property pass does not include objects `0x01D0` /
  `0x01D1` as shot/contact body hazards; the threat is their emitted projectile.

### Runtime change

Added `OpenAgentApp.enemy_body_contact_uses_generic_hurt()` and routed
`check_enemy_touch()` through it.  The generic fallback now explicitly excludes
actor families whose contact behavior is handled elsewhere or known negative:

- `stationary_shooter`,
- `state2b_anim`,
- `state2c_anim`,
- `state17_landmine`,
- `state23_contact_bomb`,
- `state29_money_bag`.

This does **not** claim the entire generic body-contact policy is finished.  It
prevents the known false positive and records the remaining work as a future
ASM-derived allowlist audit.

### Regression check

`tools/check_stationary_shooter_accuracy.py` now checks the path that was missed
before:

```bash
python tools/check_stationary_shooter_accuracy.py
```

The new probe overlaps the player with a raw `0x52` launcher and calls
`OpenAgentApp.check_enemy_touch()` directly.  `hurt_player()` must not be called.

## Raw `0xA7` barrel release / pushed-off-edge fall

No new barrel gameplay code was changed in this pass because the next suspected
mismatch needs a deeper trace rather than another reconstruction.

Current verified / guarded pieces remain:

- player/barrel contact uses the ASM `x+3..x+12`, `y..y+15` overlap rectangle,
- the Python barrel fall path keeps X fixed and does not let side-body collision
  stop downward falling,
- `release_barrel_against_wall()` no longer performs the unsupported horizontal
  counter-nudge removed in pass 120.

Current explicit gap:

- `SAM1:0x8542..0x8742` / state `0x1389` still needs a full model or a proof that
  the current transient representation is sufficient.
- Pushed-off-edge fall timing should be checked against a DOSBox reference or a
  complete trace of the post-push unsupported transition before more code is
  changed.

## Files changed

- `openagent/runtime.py`
- `tools/check_stationary_shooter_accuracy.py`
- `dissassembly/annotated/SAM1_tick_accuracy_excerpts.asm`
- `docs/TICK_ACCURACY_LEDGER.md`
- `docs/registry/tick_accuracy_ledger.json`
- `docs/registry/mechanics_status.json`
- `docs/ASM_EVIDENCE_INDEX.md`
- `docs/MECHANICS_INDEX.md`
- `docs/NEXT_RESEARCH_QUEUE.md`
- `docs/PASS_INDEX.md`

## Validation

```bash
python tools/check_stationary_shooter_accuracy.py
python tools/check_handoff.py
```
