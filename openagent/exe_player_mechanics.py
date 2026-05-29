from __future__ import annotations

from dataclasses import dataclass

# Small, hand-curated constants whose locations are now backed by
# tools/extract_sa_player_mechanics.py and docs/derived_mechanics.
# They are intentionally separated from gameplay tuning so we can progressively
# replace prototype physics with EXE-shaped behaviour.

ACTOR_RECORD_SIZE = 0x20
ACTOR_BASE_OFFSET = 0x34CC

ACTOR_X_OFFSET = 0x02       # DS:34ce + slot*0x20
ACTOR_Y_OFFSET = 0x04       # DS:34d0 + slot*0x20
ACTOR_PREV_X_OFFSET = 0x06  # DS:34d2 + slot*0x20
ACTOR_PREV_Y_OFFSET = 0x08  # DS:34d4 + slot*0x20
ACTOR_COUNTER_OFFSET = 0x0A # DS:34d6 + slot*0x20
ACTOR_DIR_X_OFFSET = 0x16   # DS:34e2 + slot*0x20
ACTOR_DIR_Y_OFFSET = 0x18   # DS:34e4 + slot*0x20
ACTOR_SPEED_OFFSET = 0x1A   # DS:34e6 + slot*0x20
ACTOR_STATE_OFFSET = 0x1C   # DS:34e8 + slot*0x20
ACTOR_SKIP_OFFSET = 0x1E    # DS:34ea + slot*0x20

PLAYER_X_ADDR = 0x34EE
PLAYER_Y_ADDR = 0x34F0
PLAYER_PREV_X_ADDR = 0x34F2
PLAYER_PREV_Y_ADDR = 0x34F4
PLAYER_ANIM_STATE_ADDR = 0x3500

PLAYER_JUMP_ACTIVE_FLAG = 0x69F5
PLAYER_JUMP_TIMER_ADDR = 0x69F6
PLAYER_JUMP_TIMER_INIT = 0x23

# Collision formulas recovered from SAM1 around 0x5a37 and overlap routine 0x53c4.
ACTOR_COLLISION_TOP_OFFSET = 0
ACTOR_COLLISION_BOTTOM_OFFSET = 15
ACTOR_COLLISION_RIGHT_TILE_DELTA = 1
PLAYER_OVERLAP_WIDTH_MINUS_ONE = 9
PLAYER_OVERLAP_HEIGHT_MINUS_ONE = 15

# The original upward jump/bounce is table driven.  The table contents are not
# reconstructed yet, so runtime.py still uses its temporary continuous physics.
# Keeping this flag false makes that limitation explicit and searchable.
JUMP_DISPLACEMENT_TABLE_RECOVERED = False


@dataclass(frozen=True)
class ExeJumpModel:
    active_flag_addr: int = PLAYER_JUMP_ACTIVE_FLAG
    timer_addr: int = PLAYER_JUMP_TIMER_ADDR
    timer_init: int = PLAYER_JUMP_TIMER_INIT
    displacement_expression: str = "player_y -= word[DS:69f6 + ((--timer) << 1)]"
    notes: str = (
        "SAM1 0x1a6b..0x1ae8 copies player x/y to previous x/y, toggles "
        "animation 0x0f/0x10, decrements byte 69f6, loads a word indexed by "
        "the remaining timer, and subtracts it from DS:34f0."
    )


EXE_JUMP_MODEL = ExeJumpModel()
