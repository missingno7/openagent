# Pass 107 — cleanup and documentation refresh

Scope: cleanup-only pass after the death/platform overworld work.  No gameplay
mechanics were intentionally changed.

## Code cleanup

- Removed obsolete mission fixed-step wrappers from `openagent/runtime.py`:
  - `update_player_death(dt)`
  - `update_player(dt)`
  - `update_entities(dt)`
- Removed the now-unused `_pending_player_snapshot_ticks` field and its reset
  sites.  Since pass 104, missions advance through `update_mission_simulation()`
  with one shared accumulator and one shared snapshot phase, so the older
  player/entity wrapper loops were dead code.
- Removed unused imports left by earlier overworld/death passes.
- Expanded `tools/audit_project.py` so it parses both `openagent/` and `tools/`
  sources, not only the runtime package.
- Added `tools/check_handoff.py`, a bytecode-free handoff check runner.  It
  removes stale `__pycache__` directories, AST-parses Python sources, runs the
  smoke tests, runs the mechanics registry audit, runs the project audit, and
  removes bytecode again before exit.

## Documentation cleanup

Updated the top-level and navigation docs so new work starts from the current
state instead of older pass notes:

- `README.md`
- `docs/PROJECT_MAP.md`
- `docs/PERFORMANCE_NOTES.md`
- `docs/NEXT_RESEARCH_QUEUE.md`
- `docs/OVERWORLD_RESEARCH.md`
- `docs/PASS_INDEX.md`
- `docs/exe_mechanisms_summary.md`

## Validation

```text
python tools/check_handoff.py
```

The script includes these checks:

```text
python tools/check_render_interpolation.py
python tools/check_overworld_collision.py
python tools/check_death_reset.py
python tools/check_death_camera_platform.py
python tools/audit_mechanics_status.py
python tools/audit_project.py
```
