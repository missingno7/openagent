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

PLAYER_NORMAL_JUMP_ACTIVE_FLAG = 0x6EC1
PLAYER_VERTICAL_COUNTER_ADDR = 0x34EA
PLAYER_VERTICAL_TABLE_ADDR = 0x34AF

# Collision formulas recovered from SAM1 around 0x5a37 and overlap routine 0x53c4.
ACTOR_COLLISION_TOP_OFFSET = 0
ACTOR_COLLISION_BOTTOM_OFFSET = 15
ACTOR_COLLISION_RIGHT_TILE_DELTA = 1
PLAYER_OVERLAP_WIDTH_MINUS_ONE = 9
PLAYER_OVERLAP_HEIGHT_MINUS_ONE = 15

# The ordinary mission jump/fall table is initialized at SAM1:0x28ED6..0x28F30
# and recovered exactly. DS:69F5/DS:69F6 is a distinct bounce/death-style path.
NORMAL_JUMP_DISPLACEMENT_TABLE_RECOVERED = True


@dataclass(frozen=True)
class ExeNormalJumpModel:
    active_flag_addr: int = PLAYER_NORMAL_JUMP_ACTIVE_FLAG
    counter_addr: int = PLAYER_VERTICAL_COUNTER_ADDR
    table_addr: int = PLAYER_VERTICAL_TABLE_ADDR
    displacement_expression: str = "player_y -= byte[DS:34af + (++DS:34ea)]"
    notes: str = (
        "SAM1 0xbced..0xbcf7 starts the normal jump with DS:6ec1=1 and "
        "DS:34ea=0. SAM1 0xbd06..0xbd7e increments the counter and subtracts "
        "the shared byte-table step from DS:34f0. At counter 0x0a it clears "
        "DS:6ec1, rewinds to 9, and still applies table[9] in that tick."
    )


EXE_NORMAL_JUMP_MODEL = ExeNormalJumpModel()
