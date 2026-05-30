# Project Map

This cleanup pass makes the repository easier to navigate without changing gameplay logic.

## Runtime layer: `openagent/`

| File | Purpose | Notes |
|---|---|---|
| `runtime.py` | Main Tk loop and gameplay orchestration | Still large, but HUD, player state/lifecycle, and combat/projectiles have been extracted; keep moving self-contained systems out by safe blocks. |
| `entities.py` | Runtime entity dataclasses and level extraction | Good place for actor/projectile data shapes, not behavior. |
| `combat.py` | Projectile spawning/update, combat hit policy, score popups, and actor hit helpers | Cleanup-only mixin extracted in pass 74. Future projectile/hit ASM findings should start here. |
| `semantics.py` | Raw map-code categories and source-code meaning | Add raw-code classification here before touching runtime logic. |
| `animation.py` | Player/enemy tile-frame mapping | Put frame ranges here, especially when verified from ASM. |
| `player.py` | Player runtime dataclass/state fields | Keep state shape here; keep movement behavior in runtime or a future player system. |
| `hud.py` | Status bar + 8×8 UI text renderer | Owns `SAM?02.GFX` page constants and fallback glyphs; no gameplay mutation. |
| `sound.py` | `.SND` loading/playback and sound IDs | Keep ASM sound IDs here; avoid ad-hoc numbers in runtime. |
| `sprites.py` | 16x16 and 8x8 sprite lookup helpers | HUD/menu graphics should flow through this layer, not hand-drawn masks. |
| `level_model.py` | Runtime grid/cell helpers | Shared source of truth for map-cell iteration/collision grid input. |
| `exe_*` modules | Data extracted from ASM/disassembly | These should be small, factual, and cited in docs. |

## Asset/editor layer: `secret_agent_editor/`

| File | Purpose |
|---|---|
| `graphics.py` | ProGraphx 16x16 and 8x8 decoders. Camoto cross-checks belong here. |
| `render.py` | Static level rendering from original map/tiles. |
| `bundle.py` | Episode asset loading. |
| `tile_animations.py` | Static animated tile mapping. |
| `gui.py` | Editor UI; should not become gameplay source of truth. |

## Reverse-engineering layer

| Path | Purpose |
|---|---|
| `dissassembly/` | Unpacked EXE and linear ASM references. Keep raw evidence here. |
| `tools/` | Scripts that extract structured facts from ASM/assets. |
| `docs/passes/` | Chronological pass notes. Useful for audits, not for onboarding. |
| `docs/derived_mechanics/` | JSON/CSV extracted facts used for implementation. |

## Recommended next refactors

1. Continue splitting `openagent/runtime.py` by safe systems: next best targets are `projectiles.py`, `damage.py`, `interactions.py`, and `renderer.py`.
2. Replace remaining magic object IDs in runtime with names from `semantics.py`, `animation.py`, `sound.py`, or a new factual `object_ids.py`.
3. Keep UI/HUD work tied to `SAM?02.GFX` and ASM pointer pages (`DS:6E36`, `DS:6E3A`, `DS:6E32`). Do not reintroduce PIL-drawn fake glyphs except as explicit fallback for missing data.
4. When adding mechanics, update `docs/MECHANICS_INDEX.md` and add a short pass note under `docs/passes/`.
### New cleanup modules from pass 73

- `openagent/game_constants.py` – shared dimensions, DOS tick rate, player physics tables, ammo constants. Keep pure constants here only.
- `openagent/player_lifecycle.py` – player damage/death/respawn lifecycle. Put ASM-backed hurt/death changes here instead of `runtime.py`.

## Accuracy tracking added in pass 76

Use these files before changing gameplay logic:

```text
docs/ACCURACY_STATUS.md              status labels and workflow
docs/ASM_EVIDENCE_INDEX.md           quick human-readable evidence map
docs/registry/mechanics_status.json  machine-readable mechanic registry
tools/audit_mechanics_status.py      registry validator
```

When a mechanic is changed, update its registry entry.  If behavior is discovered to be wrong during playtesting, downgrade the status instead of leaving it looking verified.
