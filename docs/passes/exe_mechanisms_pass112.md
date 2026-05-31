# Pass 112 — Bugfix: hard-death visual lookup import

Scope: regression fix after the pass-111 movement/collision extraction. No intended gameplay or ASM behavior change.

## What broke

`OpenAgentApp.runtime_visual_ids_for_code()` still lives in `runtime.py` because the mission interaction dispatcher calls it from `check_hard_death_tile_touch()`. Pass 111 trimmed imports too aggressively and removed the `runtime_cell_writes_for_code` import that this helper needs.

The crash appeared only when the player interaction path reached a hard-death runtime visual lookup, so `python run_openagent.py --help` and the previous handoff checks did not catch it.

## Fix

- Restored the explicit import from `openagent.exe_runtime_collision` in `runtime.py`.
- Added `tools/check_runtime_hard_death_import.py` to exercise the exact runtime helper used by hard-death tile checks.
- Added that smoke test to `tools/check_handoff.py`.

## Validation

```text
python tools/check_runtime_hard_death_import.py
python tools/check_handoff.py
python run_openagent.py --help
```

All passed after the fix.
