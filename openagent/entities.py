from __future__ import annotations

from dataclasses import dataclass

from .level_model import iter_map_cells
from .exe_actor_mechanics import (
    BANK14_GUARD_BEHAVIOUR_BY_BASE_TILE,
    BANK14_GUARD_SHOOT_TIMER_RANGE_BY_BASE_TILE,
    BANK14_GUARD_SPEED_BY_BASE_TILE,
    SPECIAL_ACTOR_MODELS,
    deterministic_direction,
    deterministic_range,
)
from .semantics import (
    BANK14_GUARD_CODES,
    BANK14_GUARD_INFO,
    MOVING_PLATFORM_CODE,
    RIDING_ENEMY_CODE,
    WALKER_ENEMY_CODES,
)

from secret_agent_editor.constants import TILE
from secret_agent_editor.levels import LevelInfo


# Per-code actor step values extracted from the EXE special actor table.
# DS:34E6 is a literal per-DOS-tick pixel step.  Codes not yet fully modelled
# keep a conservative fallback, but already decoded entries come from
# openagent.exe_actor_mechanics.SPECIAL_ACTOR_MODELS.
WALKER_STEP_BY_CODE: dict[int, int] = {
    RIDING_ENEMY_CODE: SPECIAL_ACTOR_MODELS.get(RIDING_ENEMY_CODE, SPECIAL_ACTOR_MODELS[0x65]).step_px,
    0x75: 1,  # EXE stores 0 here; this actor's full state logic is not yet implemented.
    0x76: 1,  # EXE stores 0 here; this actor's full state logic is not yet implemented.
    0x6E: SPECIAL_ACTOR_MODELS[0x6E].step_px,
}

@dataclass
class MovingPlatform:
    x: float
    y: float
    # EXE actor direction DS:34E2 is +1 or -1.  User/gameplay check: the
    # visible moving platform starts by travelling left.
    direction: int = -1
    # EXE actor speed field DS:34E6 is a per-game-tick pixel step, not px/sec.
    step_px: int = 1
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
    direction: int = 1
    # EXE field DS:34E6: pixels per DOS game tick.
    step_px: int = 1
    anim_time: float = 0.0
    frame_counter: int = 0x01
    bank: int | None = None
    base_tile: int | None = None
    shoot_interval_ticks: int = 0
    shoot_timer_ticks: int = 0
    alert_ticks: int = 0
    kind: str = "walker"
    behavior_state: int = 0
    object_id: int = 0

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

    @property
    def is_rip(self) -> bool:
        return self.kind == "rip"

    @property
    def can_shoot(self) -> bool:
        return self.shoot_interval_ticks > 0 and not self.is_rip


@dataclass
class Projectile:
    x: float
    y: float
    direction: int
    speed: float = 175.0
    hostile: bool = False


@dataclass
class ScorePopup:
    x: float
    y: float
    value: int
    tile: int
    ticks_left: int = 16


@dataclass
class LevelEntities:
    platforms: list[MovingPlatform]
    enemies: list[Enemy]
    projectiles: list[Projectile]
    score_popups: list[ScorePopup]


def extract_level_entities(info: LevelInfo) -> LevelEntities:
    platforms: list[MovingPlatform] = []
    enemies: list[Enemy] = []
    for cell in iter_map_cells(info):
        if cell.code == MOVING_PLATFORM_CODE:
            platforms.append(MovingPlatform(float(cell.x * TILE), float(cell.y * TILE), direction=-1, step_px=1))
        elif cell.code in BANK14_GUARD_CODES:
            model = BANK14_GUARD_INFO[cell.code]
            base_tile = int(model["base_tile"])
            direction = deterministic_direction(cell.code, cell.x, cell.y)
            shoot_range = BANK14_GUARD_SHOOT_TIMER_RANGE_BY_BASE_TILE.get(base_tile)
            shoot_interval = (
                deterministic_range(cell.code, cell.x, cell.y, shoot_range[0], shoot_range[1], salt=1)
                if shoot_range is not None
                else 0
            )
            enemies.append(
                Enemy(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    direction=direction,
                    step_px=BANK14_GUARD_SPEED_BY_BASE_TILE.get(base_tile, 1),
                    bank=14,
                    base_tile=base_tile,
                    shoot_interval_ticks=shoot_interval,
                    shoot_timer_ticks=shoot_interval,
                    kind="bank14_guard",
                    behavior_state=BANK14_GUARD_BEHAVIOUR_BY_BASE_TILE.get(base_tile, 0),
                    object_id=SPECIAL_ACTOR_MODELS[cell.code].object_id,
                )
            )
        elif cell.code in WALKER_ENEMY_CODES:
            actor_model = SPECIAL_ACTOR_MODELS.get(cell.code)
            direction = deterministic_direction(cell.code, cell.x, cell.y) if actor_model and actor_model.random_initial_direction else (-1 if cell.code in {0x76} else 1)
            enemies.append(
                Enemy(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    direction=direction,
                    step_px=WALKER_STEP_BY_CODE.get(cell.code, 1),
                    behavior_state=actor_model.behavior_state if actor_model else 0,
                    object_id=actor_model.object_id if actor_model else 0,
                )
            )
    return LevelEntities(platforms, enemies, [], [])
