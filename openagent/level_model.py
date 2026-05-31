from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from openagent.game_assets.constants import LEVEL_H, LEVEL_W, ROW_BYTES, ROWS_PER_LEVEL
from openagent.game_assets.levels import LevelInfo
from openagent.game_assets.render import SecretAgentRenderer


@dataclass(frozen=True)
class RuntimeCollisionCell:
    x: int
    y: int
    source_x: int
    source_y: int
    source_code: int
    source_layer: str
    body_solid: bool
    foot_solid: bool
    c6: int
    c8: int
    cA: int

@dataclass(frozen=True)
class MapCell:
    x: int
    y: int
    code: int
    raw_row: int
    layer: str


def invalidate_level_model_cache(info: LevelInfo) -> None:
    """Drop cached map-cell indexes after direct raw-level edits.

    Runtime code treats decoded level data as immutable.  Editor/research tools
    that patch ``LevelInfo.raw`` in memory should call this before asking for
    cells/collision again.
    """
    for attr in ("_map_cells_cache", "_cells_by_xy_cache", "_visual_coverage_by_xy_cache"):
        if hasattr(info, attr):
            delattr(info, attr)
    if hasattr(info, "_layout_built"):
        delattr(info, "_layout_built")


def map_cells(info: LevelInfo) -> tuple[MapCell, ...]:
    cached = getattr(info, "_map_cells_cache", None)
    if cached is not None:
        return cached

    SecretAgentRenderer.build_layout(info)
    cells: list[MapCell] = []
    for y in range(LEVEL_H):
        bg_row = info.bg_raw_for_y[y]
        if bg_row is not None:
            row = info.raw[bg_row * ROW_BYTES:bg_row * ROW_BYTES + LEVEL_W]
            cells.extend(MapCell(x, y, code, bg_row, "bg") for x, code in enumerate(row))

        fg_row = info.fg_raw_for_y[y]
        if fg_row is not None:
            row = info.raw[fg_row * ROW_BYTES:fg_row * ROW_BYTES + LEVEL_W]
            cells.extend(
                MapCell(x, y, code, fg_row, "fg")
                for x, code in enumerate(row)
                if not (x == 0 and code == ord("*"))
            )

    cached = tuple(cells)
    setattr(info, "_map_cells_cache", cached)
    return cached


def cells_by_xy(info: LevelInfo) -> dict[tuple[int, int], tuple[MapCell, ...]]:
    cached = getattr(info, "_cells_by_xy_cache", None)
    if cached is not None:
        return cached

    grouped: dict[tuple[int, int], list[MapCell]] = defaultdict(list)
    for cell in map_cells(info):
        grouped[(cell.x, cell.y)].append(cell)
    cached = {pos: tuple(cells) for pos, cells in grouped.items()}
    setattr(info, "_cells_by_xy_cache", cached)
    return cached


def iter_map_cells(info: LevelInfo) -> Iterable[MapCell]:
    return iter(map_cells(info))


def cells_at(info: LevelInfo, x: int, y: int) -> tuple[MapCell, ...]:
    if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
        return ()
    return cells_by_xy(info).get((x, y), ())


def codes_at(info: LevelInfo, x: int, y: int) -> tuple[int, ...]:
    return tuple(cell.code for cell in cells_at(info, x, y))


def raw_start_positions(info: LevelInfo, code: int) -> list[tuple[int, int]]:
    positions = []
    for raw_row in range(2, ROWS_PER_LEVEL):
        row = info.raw[raw_row * ROW_BYTES:raw_row * ROW_BYTES + LEVEL_W]
        for x, value in enumerate(row):
            if x == 0 and value == ord("*"):
                continue
            if value == code:
                positions.append((x, raw_row))
    return positions


def visual_coverage_index(info: LevelInfo) -> dict[tuple[int, int], tuple[MapCell, ...]]:
    cached = getattr(info, "_visual_coverage_by_xy_cache", None)
    if cached is not None:
        return cached

    from openagent.game_assets.mapping import TILE_MAP

    covered: dict[tuple[int, int], list[MapCell]] = defaultdict(list)
    for cell in map_cells(info):
        if cell.code in (0, 0x20, ord("*")):
            continue
        refs = TILE_MAP.get(cell.code)
        if not refs:
            covered[(cell.x, cell.y)].append(cell)
            continue
        for relx, rely, _bank, _tile_no in refs:
            tx = cell.x + relx
            ty = cell.y + rely
            if 0 <= tx < LEVEL_W and 0 <= ty < LEVEL_H:
                covered[(tx, ty)].append(cell)
    cached = {pos: tuple(cells) for pos, cells in covered.items()}
    setattr(info, "_visual_coverage_by_xy_cache", cached)
    return cached


def visual_coverage_cells(info: LevelInfo, x: int, y: int) -> tuple[MapCell, ...]:
    """Return raw map codes whose draw refs cover visual cell x/y.

    Secret Agent/Frenkel mapping stores many objects as an anchor code whose
    sprite parts are drawn at relative offsets. Runtime collision follows the
    object footprint, not just the anchor cell; otherwise multi-tile platforms
    and decorations collide at the wrong location.
    """
    if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
        return ()
    return visual_coverage_index(info).get((x, y), ())


def build_runtime_collision_grid(
    info: LevelInfo,
    *,
    removed_source_keys: set[tuple[int, int, int, str]] | frozenset[tuple[int, int, int, str]] | None = None,
    code_collision_overrides: dict[int, int] | None = None,
    world_map: bool = False,
) -> dict[tuple[int, int], RuntimeCollisionCell]:
    """Replay the EXE-derived map-token -> runtime-cell writes.

    Level 0 / overworld uses a different EXE token parser from mission maps.
    Pass ``world_map=True`` for level 0; otherwise raw codes such as 0x55 use
    mission semantics and collide incorrectly.

    The original map loader does not decide collision from the visual TILE_MAP
    footprint.  It calls a runtime-cell setter for each token.  The setter stores
    full cell records at ((x + dx), (y + dy)); later writes to the same target
    cell overwrite earlier collision flags.  The dx/dy offsets are generated
    after correcting the EXE's column-major runtime-buffer addressing: the
    0xC8 stride is an X-column stride, not a screen-row stride.
    Foreground/star rows pass a non-zero
    marker to the setter, which takes the EXE's visual-only branch and does not
    update +0x1CC/+0x1CD collision flags.
    """
    if world_map:
        from .exe_world_collision import world_runtime_cell_writes_for_code as runtime_cell_writes_for_code
    else:
        from .exe_runtime_collision import runtime_cell_writes_for_code

    removed_source_keys = removed_source_keys or frozenset()
    code_collision_overrides = code_collision_overrides or {}
    grid: dict[tuple[int, int], RuntimeCollisionCell] = {}
    for cell in iter_map_cells(info):
        source_key = (cell.x, cell.y, cell.code, cell.layer)
        if source_key in removed_source_keys:
            continue
        collision_code = code_collision_overrides.get(cell.code, cell.code)
        for write in runtime_cell_writes_for_code(collision_code):
            if write.requires_bg_row and cell.layer != "bg":
                # In the original setter, a non-zero row marker jumps to the
                # branch that writes only +0x1CA for rendering.  It leaves
                # +0x1CC/+0x1CD collision untouched, so for collision-grid
                # reconstruction this write is ignored.
                continue
            tx = cell.x + write.dx
            ty = cell.y + write.dy
            if not (0 <= tx < LEVEL_W and 0 <= ty < LEVEL_H):
                continue
            grid[(tx, ty)] = RuntimeCollisionCell(
                x=tx,
                y=ty,
                source_x=cell.x,
                source_y=cell.y,
                source_code=cell.code,
                source_layer=cell.layer,
                body_solid=write.body_solid,
                foot_solid=write.foot_solid,
                c6=write.c6,
                c8=write.c8,
                cA=write.cA,
            )
    return grid


def runtime_collision_cell_at(
    info: LevelInfo,
    x: int,
    y: int,
    *,
    removed_source_keys: set[tuple[int, int, int, str]] | frozenset[tuple[int, int, int, str]] | None = None,
) -> RuntimeCollisionCell | None:
    if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
        return None
    return build_runtime_collision_grid(info, removed_source_keys=removed_source_keys).get((x, y))
