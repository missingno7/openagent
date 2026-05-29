# OpenAgent

OpenAgent is a work-in-progress reverse-engineered source port for Apogee's
Secret Agent trilogy.

This workspace starts from three local inputs:

- `OpenCrystalCaves/`: an existing source port for Crystal Caves, a closely
  related Apogee engine.
- `dissassembly/`: unpacked Secret Agent executables, linear 8086 disassembly,
  strings, and MZ metadata for `SAM1`, `SAM2`, and `SAM3`.
- `game_data/`: the original Secret Agent data files used as the behavioral and
  asset reference.

## Current Status

The project is a Python reverse-engineering harness and early playable runtime,
not a complete source port yet.  It already loads all three episodes through the
original data files, reconstructs much of the EXE-derived mission collision
model, and promotes many moving objects from static map bytes into runtime
actors.

Run the current inventory tool with:

```powershell
python tools\inspect_secret_agent_assets.py --markdown docs\asset_inventory.md
```

Optional PCX preview extraction:

```powershell
python tools\inspect_secret_agent_assets.py --extract-pcx artifacts\pcx_previews
```

The previews are written as binary PPM files so they do not need Pillow or other
third-party Python packages.

## Running The Prototype

The first OpenAgent runtime loads all three Secret Agent episodes through the
`secret_agent_editor` data loader and opens a small playable prototype window:

```powershell
python run_openagent.py game_data
```

If your active Python does not have Pillow installed, either install the root
requirements:

```powershell
python -m pip install -r requirements.txt
```

or run it with the Codex bundled Python runtime used during development:

```powershell
C:\Users\jiriv\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_openagent.py game_data
```

Prototype controls:

- World map: arrows/WASD move, Space/Enter opens the nearby level entrance.
- Platform levels: arrows/WASD move, Space jumps.
- Global: PgUp/PgDn changes level, Q/E changes episode, M opens the world map,
  R resets, Tab toggles raw map codes, U toggles unknown-code markers, and C
  toggles collision debug display.

## Near-Term Port Plan

1. Promote `secret_agent_editor` loaders into stable OpenAgent asset APIs for
   16x16 tiles, 8x8 sprites, level archives, PCX screens, sound records, config,
   and EXE-derived metadata.
2. Continue replacing prototype fallbacks with Secret Agent's real tile, object,
   actor and interaction behavior.
3. Add the original player sprite/animation, weapons, hazards, enemies, items,
   doors, teleporters, world-map progression, UI, sound, and menus.
4. Keep the aggregate campaign model: one runtime, three episodes, loaded from
   the original data files.

Start with `docs/reverse_engineering_status.md` for current hard assumptions,
`docs/exe_mechanisms_summary.md` for the cleaned-up EXE pass index, and
`docs/gameplay_research.md` for the gameplay-oriented overview.  The older pass
documents remain as audit logs of how each conclusion was reached.
