from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorSpawnModel:
    raw_code: int
    object_id: int
    step_px: int
    behavior_state: int
    random_initial_direction: bool = False
    timer_min: int | None = None
    timer_max: int | None = None
    aux_dc: int | None = None


# Extracted from the SAM1/SAM2/SAM3 special actor token table at CS:3A59.
# The EXE writes these fields into the 0x20-byte actor slot:
#   DS:34E0 = object/sprite id
#   DS:34E6 = per-tick pixel step
#   DS:34E8 = actor behaviour state
#   DS:34D8 = optional timer period, sometimes random(n)+base
SPECIAL_ACTOR_MODELS: dict[int, ActorSpawnModel] = {
    0x23: ActorSpawnModel(0x23, object_id=0x0097, step_px=0, behavior_state=0x20, timer_min=3, timer_max=3),
    0x38: ActorSpawnModel(0x38, object_id=0x015F, step_px=1, behavior_state=0x01, random_initial_direction=True),
    0x39: ActorSpawnModel(0x39, object_id=0x0167, step_px=1, behavior_state=0x02, random_initial_direction=True),
    0x30: ActorSpawnModel(0x30, object_id=0x016F, step_px=2, behavior_state=0x03, random_initial_direction=True),
    0x67: ActorSpawnModel(0x67, object_id=0x0177, step_px=2, behavior_state=0x04, random_initial_direction=True, timer_min=50, timer_max=99),
    0x47: ActorSpawnModel(0x47, object_id=0x017F, step_px=2, behavior_state=0x05, random_initial_direction=True, timer_min=30, timer_max=49),
    0x65: ActorSpawnModel(0x65, object_id=0x0075, step_px=2, behavior_state=0x22, random_initial_direction=True, aux_dc=3),
    0x6E: ActorSpawnModel(0x6E, object_id=0x0085, step_px=2, behavior_state=0x26, random_initial_direction=True, timer_min=30, timer_max=49, aux_dc=3),
    0x7F: ActorSpawnModel(0x7F, object_id=0x0261, step_px=2, behavior_state=0x06, random_initial_direction=True, timer_min=2, timer_max=2),
}

BANK14_GUARD_SPEED_BY_BASE_TILE: dict[int, int] = {
    0: SPECIAL_ACTOR_MODELS[0x38].step_px,
    8: SPECIAL_ACTOR_MODELS[0x39].step_px,
    16: SPECIAL_ACTOR_MODELS[0x30].step_px,
    24: SPECIAL_ACTOR_MODELS[0x67].step_px,
    32: SPECIAL_ACTOR_MODELS[0x47].step_px,
}

BANK14_GUARD_BEHAVIOUR_BY_BASE_TILE: dict[int, int] = {
    0: SPECIAL_ACTOR_MODELS[0x38].behavior_state,
    8: SPECIAL_ACTOR_MODELS[0x39].behavior_state,
    16: SPECIAL_ACTOR_MODELS[0x30].behavior_state,
    24: SPECIAL_ACTOR_MODELS[0x67].behavior_state,
    32: SPECIAL_ACTOR_MODELS[0x47].behavior_state,
}

BANK14_GUARD_SHOOT_TIMER_RANGE_BY_BASE_TILE: dict[int, tuple[int, int] | None] = {
    0: None,
    8: None,
    16: None,
    24: (50, 99),
    32: (30, 49),
}


def deterministic_actor_rng(code: int, x: int, y: int, *, salt: int = 0) -> int:
    """Small deterministic stand-in for the EXE RNG during actor spawning.

    The original code calls its RNG while parsing actors, e.g. random(2) for
    initial direction and random(n)+base for shooter timers.  The editor runtime
    should stay reproducible when a level reloads, so this hashes the actor's
    code and cell position instead of using process-global randomness.
    """
    v = (code * 1103515245 + x * 12345 + y * 2654435761 + salt * 97531) & 0xFFFFFFFF
    v ^= (v >> 16)
    return v & 0x7FFFFFFF


def deterministic_range(code: int, x: int, y: int, lo: int, hi: int, *, salt: int = 0) -> int:
    if hi <= lo:
        return lo
    return lo + deterministic_actor_rng(code, x, y, salt=salt) % (hi - lo + 1)


def deterministic_direction(code: int, x: int, y: int) -> int:
    # Mirrors random(2): non-zero -> +1, zero -> -1.
    return 1 if deterministic_actor_rng(code, x, y) % 2 else -1

# Spike trap actors extracted from the same special-low actor table as the
# bank-14 guards.  Raw 0x3F is the floor spike trap and raw 0x41 is the ceiling
# spike trap.  The EXE does not animate them as a background tile.  It creates
# an actor slot with:
#   state 0x11 / 0x12, object id 0x01B3 while idle, period DS:34D8 = 0x1E,
#   timer DS:34DA = random(0x1E).
# Once the timer reaches the period it selects:
#   floor:   object = 0x01D7 + ((timer - period) >> 2)  -> bank 4 tiles 20..27
#   ceiling: object = 0x01DF + ((timer - period) >> 2)  -> bank 4 tiles 28..35
# At timer 0x3C the actor resets to the idle object and repeats.
SPIKE_FLOOR_CODE = 0x3F
SPIKE_CEILING_CODE = 0x41
SPIKE_PERIOD_TICKS = 0x1E
SPIKE_CYCLE_TICKS = 0x3C
SPIKE_IDLE_OBJECT_ID = 0x01B3
SPIKE_FLOOR_STATE = 0x11
SPIKE_CEILING_STATE = 0x12
SPIKE_FLOOR_VISUAL_BASE_ID = 0x01D7
SPIKE_CEILING_VISUAL_BASE_ID = 0x01DF
SPIKE_FLOOR_BANK4_BASE_TILE = 20
SPIKE_CEILING_BANK4_BASE_TILE = 28

def spike_initial_timer(code: int, x: int, y: int) -> int:
    # Mirrors random(0x1E), but deterministic for editor/runtime reloads.
    return deterministic_actor_rng(code, x, y, salt=0x51) % SPIKE_PERIOD_TICKS

def spike_frame_for_timer(kind: str, timer: int) -> tuple[int, int] | None:
    if timer < SPIKE_PERIOD_TICKS:
        return None
    local = max(0, timer - SPIKE_PERIOD_TICKS)
    phase = min(7, local >> 2)
    base = SPIKE_CEILING_BANK4_BASE_TILE if kind == "ceiling" else SPIKE_FLOOR_BANK4_BASE_TILE
    return (4, base + phase)

def spike_is_dangerous(timer: int) -> bool:
    # The EXE checks collision while the draw object is active.  The first frame
    # is barely emerging; make frames 2..7 harmful in the prototype.
    return timer >= SPIKE_PERIOD_TICKS + 4
