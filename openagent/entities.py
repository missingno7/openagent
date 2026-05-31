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
    BEAM_HORIZONTAL_CODE,
    BEAM_PERIOD_TICKS,
    beam_initial_timer,
    SHARK_SWIMMER_CODE,
    SHARK_SWIMMER_STEP_PX,
    SHARK_SWIMMER_OBJECT_ID,
    SHARK_SWIMMER_STATE,
    FIRE_WALKER_CODE,
    FIRE_WALKER_STEP_PX,
    FIRE_WALKER_STATE,
    SATELLITE_OBJECT_ID,
    SATELLITE_HP,
    STATE27_SHOOTER_CODE,
    STATE1E_SHOOTER_CODE,
    STATE1F_SHOOTER_CODE,
    STATE23_CONTACT_BOMB_CODE,
    STATE24_UP_LASER_CODE,
    STATE2B_ANIM_CODE,
    STATE2B_ANIM_PERIOD,
    STATE2C_ANIM_PERIOD,
    STATE29_MONEY_BAG_IDLE_OBJECT_ID,
    STATE06_CONTACT_FLOATER_CODE,
    STATE17_LANDMINE_IDLE_OBJECT_ID,
    STATE17_LANDMINE_PERIOD,
    STATE17_LANDMINE_STATE,
)
from .animation import state1f_walk_counter_start
from .semantics import (
    BANK14_GUARD_CODES,
    BANK14_GUARD_INFO,
    CEILING_SPIKE_CODE,
    MOVING_PLATFORM_CODE,
    PUSHABLE_BARREL_CODE,
    RIDING_ENEMY_CODE,
    ROTATING_SATELLITE_CODE,
    SPIKE_TRAP_CODES,
    BEAM_TRAP_CODES,
    WALKER_ENEMY_CODES,
    MULTI_TILE_ACTOR_CODES,
    STATIONARY_SHOOTER_CODES,
    ANIMATED_SPECIAL_CODES,
    STATE29_MONEY_BAG_DYNAMIC_CODES,
    STATE17_LANDMINE_CODES,
)

from openagent.game_assets.constants import TILE
from openagent.game_assets.levels import LevelInfo


# Per-code actor step values extracted from the EXE special actor table.
# DS:34E6 is a literal per-DOS-tick pixel step.  Codes not yet fully modelled
# keep a conservative fallback, but already decoded entries come from
# openagent.exe_actor_mechanics.SPECIAL_ACTOR_MODELS.
WALKER_STEP_BY_CODE: dict[int, int] = {
    RIDING_ENEMY_CODE: SPECIAL_ACTOR_MODELS.get(RIDING_ENEMY_CODE, SPECIAL_ACTOR_MODELS[0x65]).step_px,
    0x75: SPECIAL_ACTOR_MODELS[0x75].step_px,
    0x76: SPECIAL_ACTOR_MODELS[0x76].step_px,
    0x6E: SPECIAL_ACTOR_MODELS[0x6E].step_px,
    0x7F: SPECIAL_ACTOR_MODELS[0x7F].step_px,
    SHARK_SWIMMER_CODE: SHARK_SWIMMER_STEP_PX,
    FIRE_WALKER_CODE: FIRE_WALKER_STEP_PX,
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
    grounded: bool = False
    fall_ticks: int = 0

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
    # EXE DS:34CC.  Projectile-hit branches set this to 3; the render loop
    # then draws the actor through an alternate white/bright sprite path and
    # decrements it.  Keep it separate from alert_ticks, which the port uses
    # for AI pauses and other behaviour timers.
    hit_flash_ticks: int = 0
    kind: str = "walker"
    behavior_state: int = 0
    object_id: int = 0
    hp: int = 1
    # Extra EXE actor timers used by states that have more than one private
    # counter beyond the generic shooting timer. For example state 0x27/raw
    # 0x24 uses DS:34DE as a walk/open phase timer and DS:34DC as the short
    # stationary/open hold counter.
    phase_ticks: int = 0
    aux_ticks: int = 0

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
    object_id: int = SATELLITE_OBJECT_ID
    hp: int = SATELLITE_HP
    hit_flash_ticks: int = 0


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
    owner: str = "enemy"
    impact_ticks: int = 0
    # State 0x1388/object 0x0187 is the transient projectile-impact slot.
    # It is visible for wall/solid impacts, but enemy hits can consume the
    # shot without drawing the big wall spark.
    impact_visible: bool = True
    life_ticks: int = 0
    # Some EXE projectile states use a narrow 10x16 actor rectangle rather
    # than the normal point/segment bullet test.  State 0x89 (ceiling crawler
    # beam) routes that rectangle through generic helper 0x53C4, while state
    # 0x25 (object-0x72 up-laser) writes the hard-death fields directly.  In
    # both cases the player side of the comparison is the 10x16 origin rect
    # DS:34EE..+9 / DS:34F0..+15, not the full 16x20 decoded sprite.
    hard_death_on_hit: bool = False
    narrow_hurt_on_hit: bool = False
    keep_on_player_hit: bool = False
    hit_w: int = 1
    hit_h: int = 1
    impact_visible_on_solid: bool = True
    impact_ticks_on_solid: int = 12

    @property
    def is_impact(self) -> bool:
        return self.impact_ticks > 0


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
        elif cell.code in ANIMATED_SPECIAL_CODES:
            actor_model = SPECIAL_ACTOR_MODELS[cell.code]
            period = STATE2B_ANIM_PERIOD if cell.code == STATE2B_ANIM_CODE else STATE2C_ANIM_PERIOD
            initial_frame = (deterministic_range(cell.code, cell.x, cell.y, 1, 5, salt=6) if cell.code == STATE2B_ANIM_CODE else 1)
            enemies.append(
                Enemy(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    direction=1,
                    step_px=0,
                    frame_counter=initial_frame,
                    shoot_interval_ticks=period,
                    shoot_timer_ticks=0,
                    kind=("state2b_anim" if cell.code == STATE2B_ANIM_CODE else "state2c_anim"),
                    behavior_state=actor_model.behavior_state,
                    object_id=actor_model.object_id,
                    hp=0,
                )
            )
        elif cell.code in STATE17_LANDMINE_CODES:
            enemies.append(
                Enemy(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    direction=1,
                    step_px=0,
                    frame_counter=1,
                    shoot_interval_ticks=STATE17_LANDMINE_PERIOD,
                    shoot_timer_ticks=0,
                    kind="state17_landmine",
                    behavior_state=STATE17_LANDMINE_STATE,
                    object_id=STATE17_LANDMINE_IDLE_OBJECT_ID,
                    hp=0,
                )
            )
        elif cell.code in STATE29_MONEY_BAG_DYNAMIC_CODES:
            actor_model = SPECIAL_ACTOR_MODELS[cell.code]
            enemies.append(
                Enemy(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    direction=1,
                    step_px=0,
                    frame_counter=1,
                    shoot_interval_ticks=0,
                    shoot_timer_ticks=0,
                    kind="state29_money_bag",
                    behavior_state=actor_model.behavior_state,
                    object_id=STATE29_MONEY_BAG_IDLE_OBJECT_ID,
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
            direction = (
                deterministic_direction(cell.code, cell.x, cell.y)
                if (actor_model and actor_model.random_initial_direction) or cell.code == FIRE_WALKER_CODE
                else (-1 if cell.code in {0x76} else 1)
            )
            shoot_interval = (
                deterministic_range(cell.code, cell.x, cell.y, actor_model.timer_min or 30, actor_model.timer_max or 49, salt=4)
                if actor_model and cell.code in {0x63, 0x6E, STATE27_SHOOTER_CODE, STATE24_UP_LASER_CODE, STATE1E_SHOOTER_CODE, STATE1F_SHOOTER_CODE}
                else 0
            )
            enemies.append(
                Enemy(
                    float(cell.x * TILE),
                    float(cell.y * TILE),
                    code=cell.code,
                    direction=direction,
                    step_px=WALKER_STEP_BY_CODE.get(cell.code, 1),
                    frame_counter=(state1f_walk_counter_start(direction) if cell.code == STATE1F_SHOOTER_CODE else 0x01),
                    shoot_interval_ticks=shoot_interval,
                    # State 0x21 increments DS:34DA every actor tick.  If the
                    # player is not under it when the period is reached, the EXE
                    # decrements the timer back to period-1, leaving the shooter
                    # armed so the next valid under-column tick fires immediately.
                    shoot_timer_ticks=(
                        (max(0, shoot_interval - 1)) if cell.code == 0x63
                        # State 0x26/raw 0x6E drives for its DS:34D8-derived
                        # interval, then stops and spawns object 0x89.  Earlier
                        # code started it in the stopped/lightning phase, which
                        # made it look like it never did the drive-then-fire
                        # cycle from the original actor branch.
                        else shoot_interval if cell.code == 0x6E
                        # State 0x1F/raw 0x58 initializes DS:34DA=0 and only
                        # fires after it has counted up to DS:34D8=0x3C.
                        else 0 if cell.code in {STATE27_SHOOTER_CODE, STATE1F_SHOOTER_CODE}
                        else shoot_interval
                    ),
                    alert_ticks=0,
                    # State 0x27/raw 0x24 init at SAM1:0x12D84..0x12DC6:
                    # DS:34D8=0x3C, DS:34DA=0, DS:34DC=3,
                    # DS:34DE=random(0x14)+0x3C.
                    phase_ticks=(
                        deterministic_range(cell.code, cell.x, cell.y, 0x3C, 0x4F, salt=6)
                        if cell.code in {STATE27_SHOOTER_CODE, STATE1F_SHOOTER_CODE}
                        else 0
                    ),
                    aux_ticks=(3 if cell.code in {STATE27_SHOOTER_CODE, STATE1F_SHOOTER_CODE} else 0),
                    kind=(
                        "ceiling_laser" if cell.code == 0x63
                        else "state1e_shooter" if cell.code == STATE1E_SHOOTER_CODE
                        else "state1f_shooter" if cell.code == STATE1F_SHOOTER_CODE
                        else "state27_shooter" if cell.code == STATE27_SHOOTER_CODE
                        else "state23_contact_bomb" if cell.code == STATE23_CONTACT_BOMB_CODE
                        else "state24_up_laser" if cell.code == STATE24_UP_LASER_CODE
                        else "lightning_flyer" if cell.code == 0x6E
                        else "fire_walker" if cell.code == FIRE_WALKER_CODE
                        else "state06_contact_floater" if cell.code == STATE06_CONTACT_FLOATER_CODE
                        else "walker"
                    ),
                    behavior_state=(FIRE_WALKER_STATE if cell.code == FIRE_WALKER_CODE else (actor_model.behavior_state if actor_model else 0)),
                    object_id=actor_model.object_id if actor_model else 0,
                    hp=(
                        ACTOR_HP_BY_OBJECT_ID.get(actor_model.object_id, actor_model.aux_dc or 1)
                        if actor_model and object_id_is_shootable(actor_model.object_id)
                        else 0
                    ),
                )
            )
    return LevelEntities(platforms, enemies, [], [], [], spike_traps, satellites, beam_traps, barrels)
