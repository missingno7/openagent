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


def codes_at(info: LevelInfo, x: int, y: int) -> tuple[int, ...]:
    if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
        return ()
    return tuple(cell.code for cell in iter_map_cells(info) if cell.x == x and cell.y == y)


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
