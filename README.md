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

Optional render-only smoothing can be enabled at launch:

```powershell
python run_openagent.py game_data --interpolate-render
```

Install the minimal Python dependency first if needed:

```powershell
python -m pip install -r requirements.txt
```

Controls:

- World map: arrows/WASD move, Space/Enter opens the nearby level entrance.
- Mission levels: arrows/WASD move, Space jumps, Ctrl fires.
- Global: PgUp/PgDn changes level, Q/E changes episode, M opens the world map, R resets, Tab toggles raw map codes, U toggles unknown-code markers, C toggles collision debug display, I toggles visual render interpolation.

## Where to look first

- `docs/PROJECT_MAP.md` — practical map of the codebase.
- `docs/PERFORMANCE_NOTES.md` — current render/lookup hot paths and benchmark notes.
- `docs/MECHANICS_INDEX.md` — implemented mechanics and where their evidence lives.
- `docs/NEXT_RESEARCH_QUEUE.md` — highest-value unknowns to tackle next.
- `docs/passes/` — chronological pass logs. These are audit history, not the main entry point.
- `openagent/runtime.py` — still the main playable loop; it is intentionally marked for future split into player, actor, projectile, interaction and render modules. Keep hot-path rendering changes aligned with `docs/PERFORMANCE_NOTES.md`.

## Cleanup policy

Keep the root clean. Temporary screenshots, decoded sprite sheets and experiment dumps belong under `artifacts/` or a throwaway `work_*` directory outside the zip. Run this before handing off a build:

```powershell
python -m compileall -q openagent tools
# remove __pycache__/ after compileall before packaging
python tools/audit_project.py
```
