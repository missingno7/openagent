# Gameplay Research

This file is now a compact gameplay entry point.  The cleaned-up mechanical
truth is in `docs/reverse_engineering_status.md`; the EXE pass index is in
`docs/exe_mechanisms_summary.md`.

## Modes

Secret Agent has two main gameplay modes:

- World map: block 0 of each `SAM?03.GFX`, top-down island movement and level
  entrance selection.
- Mission levels: blocks 1..16, side-view platforming.

The world map uses its own raw-code meaning table.  For example `0x62` is a
coastline tile on the world map, but a moving platform in mission levels.

## Hard Mission Collision Model

Mission collision is reconstructed from the EXE runtime-cell setter, not from
visible tile coverage.

- The setter is at SAM1 `0x1059e` and SAM2/SAM3 `0x1062e`.
- Runtime cells contain internal draw/object words at `+0x1C6/+0x1C8/+0x1CA`
  and collision bytes at `+0x1CC/+0x1CD`.
- Pass 5 corrected the runtime grid axes:

```text
cell = buffer + ((tile_x + 1) * 0xC8) + ((tile_y + 1) << 3)
```

- `+0x1CA` is the static object/foreground redraw path.  Normal BG codes can
  feed it too; raw `0xEB` writes `cA=0x02FC` and therefore renders in front of
  the player.
- `*` overlay rows write the overlay/object word and do not directly change
  collision flags.
- The current generated source for map-token writes is
  `openagent/exe_runtime_collision.py`.

Do not use these superseded shortcuts:

- non-empty map code means solid;
- collision follows the `TILE_MAP` visual footprint;
- BG/FG rows are normal collision layers, or a generic draw-order switch;
- the first `CS:2e20` token table decides current one-byte mission collision.

Important examples:

- `0x70`, `0x18`, `0xEA`, `0xEB`, and `0xEC` are passable in the current
  mission collision table.
- `0xD2` is a 2x2 composite whose upper cells are one-way/floor-solid.
- raw `0xD3` is not the one-way hidden platform; raw `0xD7` produces visual id
  `0x02D3` with floor collision.

## World Map

Known world-map codes:

| Code | Meaning |
| --- | --- |
| `0x59` | player icon, bank 13 tile 0 |
| `0x4D`, `0x4F`, `0x50` | entrance candidates; 16 per episode |
| `0x55` | water |
| `0x56..0x68` selected coastline codes | blocked coast/edge pieces in current model |
| `0x42..0x47` | trees/forest, blocked |

Current world-map collision is still a smaller derived model: grass/path is
passable; water, coast and trees block.  The original EXE world-map collision
and entrance table remain open research targets.

## Mission Codes

High-confidence mission raw-code meanings:

| Code | Meaning |
| --- | --- |
| `0x59` | player start, bank 13 tile 0 |
| `0x62` | moving platform |
| `0x65` | special moving enemy, state `0x22` in the special actor table |
| `0x5B` | money bag score pickup |
| `0x84` | 500-point pickup |
| `0xA7` | pushable barrel |
| `0x73` | ammo pickup, adds 5 shots, caps at 99 |
| `0x72` | reveal glasses / hidden-platform mechanic |
| `0x2B -> 0x2C` | green key and door |
| `0x2D -> 0x2E` | red key and door |
| `0x2F -> 0x34` | blue key and door |

The score/inventory dispatcher works through runtime cell `+0x1CA`, so future
pickup work should follow that path before adding raw-code behavior.

## Dynamic Actors

Moving and animated gameplay objects should be extracted into runtime entities
when the EXE allocates an actor slot for them.  Important decoded families:

- bank-14 guards: `0x38`, `0x39`, `0x30`, `0x67`, `0x47`;
- spikes: `0x3F`, `0x41`;
- stationary shooters: `0x52`, `0x51`, `0x3C`, `0x3D`;
- beam traps: `0x3B`, `0x3E`;
- rotating satellite: `0x23`;
- swimmers/walkers and special actors: `0x5F`, `0x6E`, `0x7F`, `0xAE`,
  `0x24`, `0x56`, `0x58`, `0x63`, `0x65`;
- pushable barrel: `0xA7`.

Actor state is stored in 0x20-byte records.  The key fields are object id
`34E0`, direction `34E2/34E4`, speed `34E6`, behavior state `34E8`, and frame or
timer counters `34D6/34D8/34DA`.

## OpenCrystalCaves Relevance

OpenCrystalCaves remains useful for engine architecture, state management,
renderer organization and Apogee-era data handling style.  It is not a behavior
source for Secret Agent-specific map codes, collision, actors or pickup logic.

## Next Research Targets

1. Original world-map movement constraints and entrance mapping.
2. Remaining `+0x1CA` interaction branches: doors, exits, teleporters, toggles
   and non-score pickups.
3. Exact update branches for special actors that are currently represented by
   table-derived object id/speed/timer models.
4. Player damage, lives, death/respawn and level completion.
5. Remaining sound ID naming and priority/preemption behavior inside the
   original `0x287e` playback routine.
