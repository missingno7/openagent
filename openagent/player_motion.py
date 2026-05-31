"""Pure tick transitions for the normal mission player movement path."""

from __future__ import annotations

from .game_constants import (
    FALL_COUNTER_MAX,
    JUMP_ASCENT_END_COUNTER,
    PLAYER_STEP_RAMP,
    PLAYER_TERMINAL_STEP_BASE,
    PLAYER_VERTICAL_STEP_TABLE,
    PLAYER_DEATH_BOUNCE_STEP_TABLE,
)


def horizontal_step_for_hold_ticks(hold_ticks: int, speed_bonus_step: int = 0) -> int:
    """Mirror SAM1:0x532D normal horizontal acceleration.

    ``hold_ticks`` is the EXE's DS:681E counter after the routine increments it.
    With DS:69B0=0 the first six ticks are fixed at 1,1,2,4,4,4.  From tick 7
    onward the routine returns ``DS:69A4 + 4``; DS:69A4 is normally zero and is
    set to four by the speed pickup while its timer is active.
    """
    for start, end, value in PLAYER_STEP_RAMP:
        if start <= hold_ticks <= end:
            return value
    return PLAYER_TERMINAL_STEP_BASE + max(0, int(speed_bonus_step))


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


def advance_death_bounce_tick(timer: int) -> tuple[int, bool, int]:
    """Advance the DS:69F5/DS:69F6 hard-death bounce path.

    Returns ``(new_timer, still_active, signed_step)``.  The caller should apply
    the step exactly like SAM1:0x1ABC..0x1AC0: ``player_y -= signed_step``.
    Positive values move the player upward and negative values move him down.
    When the decremented timer reaches zero the EXE calls the level restart path
    before applying another displacement.
    """
    timer = max(0, int(timer) - 1)
    if timer <= 0:
        return 0, False, 0
    if timer >= len(PLAYER_DEATH_BOUNCE_STEP_TABLE):
        return timer, True, 0
    return timer, True, PLAYER_DEATH_BOUNCE_STEP_TABLE[timer]
