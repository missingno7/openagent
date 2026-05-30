"""Pure tick transitions for the normal mission player movement path."""

from __future__ import annotations

from .game_constants import (
    FALL_COUNTER_MAX,
    JUMP_ASCENT_END_COUNTER,
    PLAYER_STEP_RAMP,
    PLAYER_VERTICAL_STEP_TABLE,
)


def horizontal_step_for_hold_ticks(hold_ticks: int) -> int:
    """Mirror SAM1:0x532D with the normal DS:69B0=0, DS:69A4=4 setup."""
    for start, end, value in PLAYER_STEP_RAMP:
        if start <= hold_ticks <= end:
            return value
    return PLAYER_STEP_RAMP[-1][2]


def advance_jump_tick(counter: int) -> tuple[int, bool, int]:
    """Advance DS:34EA for the normal DS:6EC1 jump phase.

    Returns ``(new_counter, jump_active, upward_step)``.  At counter 0x0A the
    EXE clears DS:6EC1, rewinds DS:34EA to 9, and still applies table[9] during
    that same tick.
    """
    counter = min(FALL_COUNTER_MAX, counter + 1)
    if counter == JUMP_ASCENT_END_COUNTER:
        counter = JUMP_ASCENT_END_COUNTER - 1
        return counter, False, PLAYER_VERTICAL_STEP_TABLE[counter]
    if counter >= 0x11:
        return counter, True, 0
    return counter, True, PLAYER_VERTICAL_STEP_TABLE[counter]


def advance_fall_tick(counter: int) -> tuple[int, int]:
    """Mirror SAM1:0xB8B3 counter increment, cap, and table lookup."""
    counter = min(FALL_COUNTER_MAX, counter + 1)
    return counter, PLAYER_VERTICAL_STEP_TABLE[counter]
