from __future__ import annotations

from dataclasses import dataclass

# Recovered from SAM1_unpacked_linear_8086.asm and regenerated/checkable via
# tools/extract_sa_animation_mechanics.py.

PLAYER_ANIM_STATE_ADDR = 0x3500
PLAYER_NORMAL_JUMP_ACTIVE_FLAG = 0x6EC1
PLAYER_LEFT_HELD_FLAG = 0x6ECA
PLAYER_RIGHT_HELD_FLAG = 0x6ECB
PLAYER_BOUNCE_DEATH_ACTIVE_FLAG = 0x69F5
PLAYER_BOUNCE_DEATH_TIMER_ADDR = 0x69F6

PLAYER_STATE_WALK_RIGHT = 0x01
PLAYER_STATE_WALK_LEFT = 0x05
PLAYER_STATE_IDLE_RIGHT = 0x09
PLAYER_STATE_IDLE_LEFT = 0x0A
PLAYER_STATE_RIGHT_ALT = 0x0B
PLAYER_STATE_AIR_RIGHT = 0x0D
PLAYER_STATE_AIR_LEFT = 0x0E
PLAYER_STATE_BOUNCE_DEATH_A = 0x0F
PLAYER_STATE_BOUNCE_DEATH_B = 0x10

# The EXE does not have a simple monotonically-incrementing player walk counter
# in the same way as actor records.  Keyboard press/release and collision paths
# explicitly write these state ids; the renderer then chooses the corresponding
# sprite frame elsewhere.
PLAYER_STATE_NAMES = {
    PLAYER_STATE_WALK_RIGHT: "walk/right base",
    PLAYER_STATE_WALK_LEFT: "walk/left base",
    PLAYER_STATE_IDLE_RIGHT: "idle/right",
    PLAYER_STATE_IDLE_LEFT: "idle/left",
    PLAYER_STATE_RIGHT_ALT: "right alternate/collision state",
    PLAYER_STATE_AIR_RIGHT: "normal jump air/right",
    PLAYER_STATE_AIR_LEFT: "normal jump air/left",
    PLAYER_STATE_BOUNCE_DEATH_A: "bounce/death frame A",
    PLAYER_STATE_BOUNCE_DEATH_B: "bounce/death frame B",
}

ACTOR_RECORD_SIZE = 0x20
ACTOR_FRAME_COUNTER_OFFSET = 0x0A  # DS:34D6 + slot*0x20
ACTOR_SPRITE_ID_OFFSET = 0x14      # DS:34E0 + slot*0x20
ACTOR_DIR_X_OFFSET = 0x16          # DS:34E2 + slot*0x20

ACTOR_WALK_RIGHT_FRAMES = range(0x01, 0x14)  # 0x01..0x13 inclusive
ACTOR_WALK_LEFT_FRAMES = range(0x15, 0x28)   # 0x15..0x27 inclusive

PLAYER_SPRITE_BANK = 13
PLAYER_SPRITE_FRAME_BYTES = 0xA0
PLAYER_DRAW_FRAME_FORMULA = "tile = DS:3500 + (DS:34F6 / 5) - 1"
PLAYER_WALK_COUNTER_ADDR = 0x34F6
PLAYER_WALK_COUNTER_STEP_ADDR = 0x3506
PLAYER_WALK_COUNTER_INIT = 1
PLAYER_WALK_COUNTER_STEP = 2
PLAYER_WALK_COUNTER_MAX = 0x13
PLAYER_HMOVE_SPEED_ADDR = 0x6820
PLAYER_HMOVE_SPEED_ROUTINE = 0x532D
PLAYER_HMOVE_STEPS = (1, 2, 4)
PLAYER_DIRECT_CLIMB_STEP = 4


@dataclass(frozen=True)
class ActorAnimationModel:
    frame_counter_offset: int = ACTOR_FRAME_COUNTER_OFFSET
    sprite_id_offset: int = ACTOR_SPRITE_ID_OFFSET
    dir_x_offset: int = ACTOR_DIR_X_OFFSET
    right_frames: tuple[int, int] = (0x01, 0x13)
    left_frames: tuple[int, int] = (0x15, 0x27)
    note: str = (
        "SAM1 actor update/collision code increments DS:34D6+slot*0x20. "
        "For horizontal walkers/platform-like actors it wraps 0x01..0x13 in one "
        "direction and 0x15..0x27 in the other; side collision negates DS:34E2. "
        "Rendering compresses each five counter values to one visible frame."
    )


ACTOR_ANIMATION_MODEL = ActorAnimationModel()


def player_state_name(state: int) -> str:
    return PLAYER_STATE_NAMES.get(state, f"unknown player anim state 0x{state:02X}")
