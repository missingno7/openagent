from __future__ import annotations

from dataclasses import dataclass

from .animation import (
    PLAYER_STATE_IDLE_RIGHT,
    PLAYER_WALK_COUNTER_START,
)
from .game_constants import PLAYER_VERTICAL_COUNTER_INITIAL


@dataclass
class Player:
    x: float = 32.0
    y: float = 32.0
    vx: float = 0.0
    vy: float = 0.0
    grounded: bool = False
    facing: int = 1
    walk_time: float = 0.0
    walk_counter: int = PLAYER_WALK_COUNTER_START
    anim_state: int = PLAYER_STATE_IDLE_RIGHT
    firing_time: float = 0.0
    fire_cooldown: float = 0.0
    fire_held: bool = False
    fire_pose_active: bool = False
    # Mirrors EXE DS:6EC1.  The vertical counter itself is fall_ticks/DS:34EA.
    jump_anim_timer: int = 0
    fall_ticks: int = PLAYER_VERTICAL_COUNTER_INITIAL
    move_hold_ticks: int = 0
    last_move_dir: int = 0
    # Mirrors DS:69A4/DS:69A6.  Normal movement has no speed bonus; the speed
    # pickup sets DS:69A4=4 until the expanded countdown reaches zero.
    speed_bonus_step: int = 0
    speed_bonus_ticks: int = 0
