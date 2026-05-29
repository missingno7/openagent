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
    spike_initial_timer,
    SPIKE_PERIOD_TICKS,
    STATIONARY_SHOOTER_DIRECTION,
    STATIONARY_SHOOTER_PROJECTILE,
    object_id_is_shootable,
    ACTOR_HP_BY_OBJECT_ID,
    BEAM_VERTICAL_CODE,
    BEAM_HORIZONTAL_CODE,
    BEAM_PERIOD_TICKS,
    beam_initial_timer,
    SHARK_SWIMMER_CODE,
    SHARK_SWIMMER_STEP_PX,
    SHARK_SWIMMER_OBJECT_ID,
    SHARK_SWIMMER_STATE,
)
from .semantics import (
    BANK14_GUARD_CODES,
    BANK14_GUARD_INFO,
    CEILING_SPIKE_CODE,
    FLOOR_SPIKE_CODE,
    MOVING_PLATFORM_CODE,
    PUSHABLE_BARREL_CODE,
    RIDING_ENEMY_CODE,
    ROTATING_SATELLITE_CODE,
    SPIKE_TRAP_CODES,
    BEAM_TRAP_CODES,
    WALKER_ENEMY_CODES,
    MULTI_TILE_ACTOR_CODES,
    STATIONARY_SHOOTER_CODES,
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
    0x7F: SPECIAL_ACTOR_MODELS[0x7F].step_px,
    SHARK_SWIMMER_CODE: SHARK_SWIMMER_STEP_PX,
    0xAE: SPECIAL_ACTOR_MODELS[0xAE].step_px,
    0x24: SPECIAL_ACTOR_MODELS[0x24].step_px,
    0x56: SPECIAL_ACTOR_MODELS[0x56].step_px,
    0x58: SPECIAL_ACTOR_MODELS[0x58].step_px,
    0x63: SPECIAL_ACTOR_MODELS[0x63].step_px,
}

@dataclass
class MovingPlatform:
    x: float
    y: float
    # EXE actor direction DS:34E2 is +1 or -1.  User/gameplay check: the
    # visible moving platform starts by travelling left.
    direction: int = -1
    # Moving platform uses the same actor-style per-tick step; the relevant
    # movement branch loads/stores a 2 px step for the normal platform in the
    # original game.
    step_px: int = 2
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
class PushableBarrel:
    x: float
    y: float
    code: int = PUSHABLE_BARREL_CODE
    direction: int = 1

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
    hp: int = 1

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
class SpikeTrap:
    x: float
    y: float
    code: int
    kind: str
    # EXE actor field DS:34DA.  Initialized to random(0x1E), then incremented
    # every actor tick.  0..0x1D = idle; 0x1E..0x3B = visible extension cycle.
    timer_ticks: int = 0
    period_ticks: int = SPIKE_PERIOD_TICKS

    @property
    def draw_y(self) -> float:
        # In the raw EXE the spike helper applies a half-tile sprite-origin
        # correction.  After converting actor slot coordinates into decoded
        # level coordinates that correction must be shifted up by 8 px; the
        # previous pass displayed both spike variants half a tile too low.
        return self.y - 16 if self.kind == "ceiling" else self.y



@dataclass
class BeamTrap:
    x: float
    y: float
    code: int
    kind: str
    # EXE DS:34DA / DS:34D8 timer pair for states 0x0F and 0x10.
    timer_ticks: int = 0
    period_ticks: int = BEAM_PERIOD_TICKS

@dataclass
class Satellite:
    x: float
    y: float
    code: int = ROTATING_SATELLITE_CODE
    # EXE special actor table gives state 0x20 and DS:34D8=3.  The visible
    # satellite is a 4-frame loop bank10 0..3 advanced by that 3-tick timer.
    frame_index: int = 0
    timer_ticks: int = 0
    period_ticks: int = 3
    behavior_state: int = 0x20
    object_id: int = 0x0097


@dataclass
class Projectile:
    x: float
    y: float
    direction: int
    # Projectile helper 0x5784 stores DS:34E6 from the caller.  Player/guard
    # shots pass speed=4, i.e. 4 DOS pixels per game tick.  The runtime now advances
    # these in fixed actor ticks, so speed is stored only as metadata.
    speed: float = 4 * 18.2065
    hostile: bool = False
    # Object id 0 maps to projectile object 0x27/state 0x07.  In the decoded
    # atlas this is the bank-1 two-frame bullet family.
    bank: int = 1
    tile_right: int = 38
    tile_left: int = 39
    dx_px: int | None = None
    dy_px: int = 0
    anim_tiles: tuple[int, ...] | None = None
    frame_counter: int = 0


@dataclass
class Explosion:
    x: float
    y: float
    # Projectile impact branch rewrites the projectile into a short hit-spark
    # actor. In the decoded atlas the visible family is bank 5 tiles 24..27.
    frame_counter: int = 0
    ticks_left: int = 12


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
    explosions: list[Explosion]
    score_popups: list[ScorePopup]
    spike_traps: list[SpikeTrap]
    satellites: list[Satellite]
    beam_traps: list[BeamTrap]
    barrels: list[PushableBarrel]


def extract_level_entities(info: LevelInfo) -> LevelEntities:
    platforms: list[MovingPlatform] = []
    enemies: list[Enemy] = []
    spike_traps: list[SpikeTrap] = []
    satellites: list[Satellite] = []
    beam_traps: list[BeamTrap] = []
    barrels: list[PushableBarrel] = []
    for cell in iter_map_cells(info):
        if cell.code == MOVING_PLATFORM_CODE:
            platforms.append(MovingPlatform(float(cell.x * TILE), float(cell.y * TILE), direction=-1, step_px=2))
        elif cell.code == ROTATING_SATELLITE_CODE:
            satellites.append(Satellite(float(cell.x * TILE), float(cell.y * TILE)))
        elif cell.code == PUSHABLE_BARREL_CODE:
            barrels.append(PushableBarrel(float(cell.x * TILE), float(cell.y * TILE)))
        elif cell.code in SPIKE_TRAP_CODES:
            kind = "ceiling" if cell.code == CEILING_SPIKE_CODE else "floor"
            spike_traps.append(
                SpikeTrap(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    kind=kind,
                    timer_ticks=spike_initial_timer(cell.code, cell.x, cell.y),
                )
            )
        elif cell.code in BEAM_TRAP_CODES:
            kind = "horizontal" if cell.code == BEAM_HORIZONTAL_CODE else "vertical"
            beam_traps.append(
                BeamTrap(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    kind=kind,
                    timer_ticks=beam_initial_timer(cell.code, cell.x, cell.y),
                )
            )
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
                    hp=1,
                )
            )
        elif cell.code in STATIONARY_SHOOTER_CODES:
            actor_model = SPECIAL_ACTOR_MODELS[cell.code]
            shoot_range = (actor_model.timer_min or 55, actor_model.timer_max or 74)
            shoot_interval = deterministic_range(cell.code, cell.x, cell.y, shoot_range[0], shoot_range[1], salt=3)
            bank, tile_r, tile_l = STATIONARY_SHOOTER_PROJECTILE[cell.code]
            enemies.append(
                Enemy(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    direction=STATIONARY_SHOOTER_DIRECTION[cell.code],
                    step_px=0,
                    shoot_interval_ticks=shoot_interval,
                    shoot_timer_ticks=shoot_interval,
                    kind="stationary_shooter",
                    behavior_state=actor_model.behavior_state,
                    object_id=actor_model.object_id,
                    hp=0,
                )
            )
        elif cell.code in WALKER_ENEMY_CODES or cell.code in MULTI_TILE_ACTOR_CODES:
            actor_model = SPECIAL_ACTOR_MODELS.get(cell.code)
            if cell.code == SHARK_SWIMMER_CODE:
                direction = deterministic_direction(cell.code, cell.x, cell.y)
                enemies.append(
                    Enemy(
                        float(cell.x * TILE),
                        float(cell.y * TILE),
                        code=cell.code,
                        direction=direction,
                        step_px=SHARK_SWIMMER_STEP_PX,
                        kind="swimmer",
                        behavior_state=SHARK_SWIMMER_STATE,
                        object_id=SHARK_SWIMMER_OBJECT_ID,
                        hp=1,
                    )
                )
                continue
            direction = deterministic_direction(cell.code, cell.x, cell.y) if actor_model and actor_model.random_initial_direction else (-1 if cell.code in {0x76} else 1)
            enemies.append(
                Enemy(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    direction=direction,
                    step_px=WALKER_STEP_BY_CODE.get(cell.code, 1),
                    shoot_interval_ticks=(deterministic_range(cell.code, cell.x, cell.y, actor_model.timer_min or 30, actor_model.timer_max or 49, salt=4) if actor_model and cell.code == 0x63 else 0),
                    shoot_timer_ticks=(deterministic_range(cell.code, cell.x, cell.y, actor_model.timer_min or 30, actor_model.timer_max or 49, salt=4) if actor_model and cell.code == 0x63 else 0),
                    kind=("ceiling_laser" if cell.code == 0x63 else "walker"),
                    behavior_state=actor_model.behavior_state if actor_model else 0,
                    object_id=actor_model.object_id if actor_model else 0,
                    hp=(
                        ACTOR_HP_BY_OBJECT_ID.get(actor_model.object_id, actor_model.aux_dc or 1)
                        if actor_model and object_id_is_shootable(actor_model.object_id)
                        else 0
                    ),
                )
            )
    return LevelEntities(platforms, enemies, [], [], [], spike_traps, satellites, beam_traps, barrels)
