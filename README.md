# OpenAgent

OpenAgent is a work-in-progress reverse-engineered Python runtime and reverse-engineering toolkit for Apogee's **Secret Agent** trilogy.

This repository is intentionally split into three layers:

- `openagent/game_assets/` — low-level original-data loaders, map graphics, level parsing and renderer code.
- `openagent/` — playable runtime, mechanics, actors, HUD, sound and EXE-derived behavior.
- `tools/` + `docs/` — reverse-engineering scripts, generated notes and audit trails.

Original game files live in `game_data/`. Disassembly references live in `dissassembly/`. The runtime should keep loading behavior from these original assets rather than hardcoding guessed replacement graphics.

## Run

```powershell
python run_openagent.py game_data
```

Optional render-only interpolation modes can be enabled at launch:

```powershell
python run_openagent.py game_data --interpolate-render  # linear previous->current poses
python run_openagent.py game_data --smooth-render       # render-only display/camera smoothing
```

Install the minimal Python dependency first if needed:

```powershell
python -m pip install -r requirements.txt
```

Controls:

- World map: arrows/WASD move; walking into a house/entrance opens that mission. Space/Enter still acts as a compatibility shortcut for the nearby entrance.
- Mission levels: arrows/WASD move, Space jumps, Ctrl fires.
- Global: PgUp/PgDn changes level, Q/E changes episode, M opens the world map, R resets, Tab toggles raw map codes, U toggles unknown-code markers, C toggles collision debug display, I cycles render interpolation off/linear/smooth.

## Where to look first

- `docs/PROJECT_MAP.md` — practical map of the codebase.
- `docs/PERFORMANCE_NOTES.md` — current render/lookup hot paths and benchmark notes.
- `docs/MECHANICS_INDEX.md` — implemented mechanics and where their evidence lives.
- `docs/TICK_ACCURACY_LEDGER.md` — ASM refs → Python tick entrypoints → blind spots → regression tests.
- `docs/NEXT_RESEARCH_QUEUE.md` — highest-value unknowns to tackle next.
- `docs/passes/` — chronological pass logs. These are audit history, not the main entry point.
- `tools/check_handoff.py` — cleanup-safe smoke/audit runner before packaging.
- `openagent/runtime.py` — application construction, level reset, frame pacing and fixed-step simulation orchestration.
- `openagent/movement_collision.py` — mission movement/collision, moving-platform and barrel support helpers.
- `openagent/rendering.py` — render-only interpolation, presentation smoothing, camera projection, static level-image refresh and Tk/PIL compositing.
- `openagent/interpolation.py` — shared render-only lerp/follow helpers used by player, actors and camera.
- `openagent/window.py` — Tk input, zoom and episode/level navigation controls.
- `openagent/teleport.py` — reconstructed teleporter countdown/touch/release state.
- `dissassembly/annotated/` — curated ASM excerpts with inline comments for tick-accuracy work.

## Cleanup policy

Keep the root clean. Temporary screenshots, decoded sprite sheets and experiment dumps belong under `artifacts/` or a throwaway `work_*` directory outside the zip. Run this before handing off a build:

```powershell
python tools/check_handoff.py
```
