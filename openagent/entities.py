from __future__ import annotations

from dataclasses import dataclass

from .level_model import iter_map_cells
from .semantics import MOVING_PLATFORM_CODE, RIDING_ENEMY_CODE

from secret_agent_editor.constants import TILE
from secret_agent_editor.levels import LevelInfo


@dataclass
class MovingPlatform:
    x: float
    y: float
    direction: int = 1
    speed: float = 32.0
    code: int = MOVING_PLATFORM_CODE

    @property
    def left(self) -> int:
        return int(self.x)

    @property
    def top(self) -> int:
        return int(self.y)

    @property
    def right(self) -> int:
        return int(self.x + TILE - 1)

    @property
    def bottom(self) -> int:
        return int(self.y + TILE - 1)


@dataclass
class Enemy:
    x: float
    y: float
    code: int = RIDING_ENEMY_CODE


@dataclass
class LevelEntities:
    platforms: list[MovingPlatform]
    enemies: list[Enemy]


def extract_level_entities(info: LevelInfo) -> LevelEntities:
    platforms: list[MovingPlatform] = []
    enemies: list[Enemy] = []
    for cell in iter_map_cells(info):
        if cell.code == MOVING_PLATFORM_CODE:
            platforms.append(MovingPlatform(float(cell.x * TILE), float(cell.y * TILE)))
        elif cell.code == RIDING_ENEMY_CODE:
            enemies.append(Enemy(float(cell.x * TILE), float(cell.y * TILE)))
    return LevelEntities(platforms, enemies)
