from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .loader import ensure_editor_importable

ensure_editor_importable(Path(__file__).resolve().parents[1])

from secret_agent_editor.constants import LEVEL_H, LEVEL_W, ROW_BYTES, ROWS_PER_LEVEL
from secret_agent_editor.levels import LevelInfo
from secret_agent_editor.render import SecretAgentRenderer


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


def iter_map_cells(info: LevelInfo) -> Iterable[MapCell]:
    SecretAgentRenderer.build_layout(info)
    for y in range(LEVEL_H):
        bg_row = info.bg_raw_for_y[y]
        if bg_row is not None:
            row = info.raw[bg_row * ROW_BYTES:bg_row * ROW_BYTES + LEVEL_W]
            for x, code in enumerate(row):
                yield MapCell(x, y, code, bg_row, "bg")

        fg_row = info.fg_raw_for_y[y]
        if fg_row is not None:
            row = info.raw[fg_row * ROW_BYTES:fg_row * ROW_BYTES + LEVEL_W]
            for x, code in enumerate(row):
                if x == 0 and code == ord("*"):
                    continue
                yield MapCell(x, y, code, fg_row, "fg")


def cells_at(info: LevelInfo, x: int, y: int) -> tuple[MapCell, ...]:
    if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
        return ()
    return tuple(cell for cell in iter_map_cells(info) if cell.x == x and cell.y == y)


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


def visual_coverage_cells(info: LevelInfo, x: int, y: int) -> tuple[MapCell, ...]:
    """Return raw map codes whose draw refs cover visual cell x/y.

    Secret Agent/Frenkel mapping stores many objects as an anchor code whose
    sprite parts are drawn at relative offsets. Runtime collision follows the
    object footprint, not just the anchor cell; otherwise multi-tile platforms
    and decorations collide at the wrong location.
    """
    if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
        return ()
    from secret_agent_editor.mapping import TILE_MAP

    covered: list[MapCell] = []
    for cell in iter_map_cells(info):
        if cell.code in (0, 0x20, ord("*")):
            continue
        refs = TILE_MAP.get(cell.code)
        if not refs:
            if cell.x == x and cell.y == y:
                covered.append(cell)
            continue
        for relx, rely, _bank, _tile_no in refs:
            if cell.x + relx == x and cell.y + rely == y:
                covered.append(cell)
                break
    return tuple(covered)


def build_runtime_collision_grid(
    info: LevelInfo,
    *,
    removed_source_keys: set[tuple[int, int, int, str]] | frozenset[tuple[int, int, int, str]] | None = None,
    code_collision_overrides: dict[int, int] | None = None,
) -> dict[tuple[int, int], RuntimeCollisionCell]:
    """Replay the EXE-derived map-token -> runtime-cell writes.

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
