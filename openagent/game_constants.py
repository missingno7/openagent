"""Runtime-wide constants that mirror Secret Agent's 320x200 DOS playfield.

This module deliberately contains only shared values, not behaviour.  Keeping
these here prevents circular imports when small runtime subsystems are split out
of ``runtime.py``.
"""

from __future__ import annotations

from .collision import PLAYER_DRAW_H, PLAYER_DRAW_W
from .hud import STATUS_BAR_H

GAME_VIEW_W = 320
GAME_VIEW_H = 200
ACTIVE_VIEW_W = 320
ACTIVE_VIEW_H = GAME_VIEW_H - STATUS_BAR_H
DEFAULT_ZOOM = 2
MIN_ZOOM = 1
MAX_ZOOM = 6
HUD_H = 0

PLAYER_W = PLAYER_DRAW_W
PLAYER_H = PLAYER_DRAW_H

# The EXE logic is paced like the DOS timer tick, not a 60 Hz render loop.
DOS_TICK_HZ = 18.2065
WORLD_MOVE_SPEED = 72.0

# Routine 0x532D selects integer horizontal step sizes from DS:681E.  In the
# normal DS:69B0=0 path the unboosted terminal step is 4 px/tick; collecting
# the speed pickup writes DS:69A4=4, so ticks 7+ become DS:69A4 + 4 = 8.
PLAYER_STEP_RAMP = ((1, 2, 1), (3, 3, 2), (4, 6, 4))
PLAYER_TERMINAL_STEP_BASE = 4
PLAYER_SPEED_BONUS_STEP = 4
# SAM1:0xD659 writes DS:69A4=4 and DS:69A6=0x00D8.  The timer ISR at
# SAM1:0x0C0A decrements DS:69A6 once per 0x14 timer ticks; store the runtime
# countdown expanded into normal fixed game ticks.
PLAYER_SPEED_BONUS_TIMER_UNITS = 0xD8
PLAYER_SPEED_BONUS_UNIT_TICKS = 0x14
PLAYER_SPEED_BONUS_TOTAL_TICKS = PLAYER_SPEED_BONUS_TIMER_UNITS * PLAYER_SPEED_BONUS_UNIT_TICKS

# Raw actor-style movement helpers use explicit per-actor speed fields
# (for example DS:34E6 in the 0x81C8 actor-candidate prelude). Several
# decoded spawn/helper call sites feed 0x04 as the actor step. Raw 0xA7 barrel
# push/fall must not borrow the player's DS:34AF vertical table.
BARREL_ACTOR_STEP_PX = 4

# Both player jump ascent and player falling use the same byte table at DS:34AF.
JUMP_ASCENT_END_COUNTER = 0x0A
FALL_COUNTER_MAX = 0x13
# SAM1:0x28ED6..0x28F30 initializes bytes 0x34B0..0x34C2, and
# B8B3/BD22 index them as ``byte[0x34AF + DS:34EA]``.  Therefore counter
# value 1 reads 0x34B0, whose value is zero.  Older project notes shifted this
# table by one slot, which made the first jump tick move up by 8px and broke the
# original jump/fall modulo-16 alignment moments used by one-tile openings.
# SAM1:0x28F35 initializes DS:34EA to 0x12. The standing B8B3 pass advances it
# to the capped terminal fall speed on the next player tick.
PLAYER_VERTICAL_COUNTER_INITIAL = 0x12
PLAYER_VERTICAL_STEP_TABLE = (
    0,  # index 0 is not normally consumed by B8B3/BD22 after their pre-increment
    0, 8, 8, 8, 4, 4, 2, 2, 2, 1, 1, 2, 2, 2, 4, 4, 8, 8, 8,
)

# Separate DS:69F5/DS:69F6 hard-death/bounce path.  SAM1 initialises
# DS:69F6 to 0x23, then each tick decrements it and reads a signed WORD from
# [DS:69F6 + (timer << 1)] before doing ``player_y -= step``.  Positive
# values therefore throw the player upward; negative values later pull him
# downward.  Index 0 is never used for movement because the EXE resets the
# level immediately when the decremented timer reaches zero.
PLAYER_DEATH_TIMER_INITIAL = 0x23
PLAYER_DEATH_BOUNCE_STEP_TABLE = (
    0,
    -8, -8, -8, -8, -8, -8, -8, -8, -8, -8, -8, -8,
    -6, -6, -6, -6, -6, -6,
    -4, -4, -4, -4,
    0, 0, 0,
    4, 4,
    8, 8, 8, 8, 8, 8, 8, 8,
)
GROUND_EPSILON = 0.35

# SAM1 new-game/init path sets DS:6858 = 5 and ammo pickups clamp it to 0x63.
STARTING_AMMO = 5
MAX_AMMO = 0x63
