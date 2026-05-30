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

# Both jump ascent and falling use the same byte table at DS:34AF.
JUMP_ASCENT_END_COUNTER = 0x0A
FALL_COUNTER_MAX = 0x13
# SAM1:0x28F35 initializes DS:34EA to 0x12. The standing B8B3 pass advances it
# to the capped terminal fall speed on the next player tick.
PLAYER_VERTICAL_COUNTER_INITIAL = 0x12
PLAYER_VERTICAL_STEP_TABLE = (
    0,
    8, 8, 8, 4, 4, 2, 2, 2, 1, 1, 2, 2, 2, 4, 4, 8, 8, 8, 8,
)
GROUND_EPSILON = 0.35

# SAM1 new-game/init path sets DS:6858 = 5 and ammo pickups clamp it to 0x63.
STARTING_AMMO = 5
MAX_AMMO = 0x63
