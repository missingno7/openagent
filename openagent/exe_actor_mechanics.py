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
    0xAE: ActorSpawnModel(0xAE, object_id=0x0353, step_px=2, behavior_state=0x2A, random_initial_direction=True, aux_dc=3),
    0x56: ActorSpawnModel(0x56, object_id=0x0321, step_px=2, behavior_state=0x1E, random_initial_direction=True, timer_min=30, timer_max=49, aux_dc=3),
    0x58: ActorSpawnModel(0x58, object_id=0x0331, step_px=2, behavior_state=0x1F, random_initial_direction=True, timer_min=60, timer_max=60, aux_dc=3),
    0x63: ActorSpawnModel(0x63, object_id=0x0345, step_px=2, behavior_state=0x21, random_initial_direction=True, timer_min=30, timer_max=49, aux_dc=3),
    0x24: ActorSpawnModel(0x24, object_id=0x0065, step_px=2, behavior_state=0x27, random_initial_direction=True, timer_min=60, timer_max=60, aux_dc=3),
    0x23: ActorSpawnModel(0x23, object_id=0x0097, step_px=0, behavior_state=0x20, timer_min=3, timer_max=3),
    0x38: ActorSpawnModel(0x38, object_id=0x015F, step_px=1, behavior_state=0x01, random_initial_direction=True),
    0x39: ActorSpawnModel(0x39, object_id=0x0167, step_px=1, behavior_state=0x02, random_initial_direction=True),
    0x30: ActorSpawnModel(0x30, object_id=0x016F, step_px=2, behavior_state=0x03, random_initial_direction=True),
    0x67: ActorSpawnModel(0x67, object_id=0x0177, step_px=2, behavior_state=0x04, random_initial_direction=True, timer_min=50, timer_max=99),
    0x47: ActorSpawnModel(0x47, object_id=0x017F, step_px=2, behavior_state=0x05, random_initial_direction=True, timer_min=30, timer_max=49),
    0x65: ActorSpawnModel(0x65, object_id=0x0075, step_px=2, behavior_state=0x22, random_initial_direction=True, aux_dc=3),
    0x6E: ActorSpawnModel(0x6E, object_id=0x0085, step_px=2, behavior_state=0x26, random_initial_direction=True, timer_min=30, timer_max=49, aux_dc=3),
    0x7F: ActorSpawnModel(0x7F, object_id=0x0261, step_px=2, behavior_state=0x06, random_initial_direction=True, timer_min=2, timer_max=2),
    0x52: ActorSpawnModel(0x52, object_id=0x01D0, step_px=0, behavior_state=0x0A, timer_min=55, timer_max=74),
    0x51: ActorSpawnModel(0x51, object_id=0x01D1, step_px=0, behavior_state=0x0B, timer_min=55, timer_max=74),
    0x3C: ActorSpawnModel(0x3C, object_id=0x01E7, step_px=0, behavior_state=0x0C, timer_min=55, timer_max=74),
    0x3D: ActorSpawnModel(0x3D, object_id=0x01EB, step_px=0, behavior_state=0x0D, timer_min=55, timer_max=74),
}

# Raw 0x5F is the bank-4 shark swimmer (bank 4 tiles 44..47 in the decoded
# atlas).  It is not present in the 0x3A59 special-low table because it is
# spawned from the regular water/enemy path, but the actor update snippets use
# the same DS:34D6 walking counter and DS:34E6-style 2 px/tick movement.
SHARK_SWIMMER_CODE = 0x5F
SHARK_SWIMMER_STEP_PX = 2
SHARK_SWIMMER_OBJECT_ID = 0x01EF
SHARK_SWIMMER_STATE = 0x28

# Projectile/player-shot interaction filter recovered from the actor-hit
# dispatcher around SAM1:0x4BD2..0x4ED5.  It does not treat every actor slot as
# damageable.  The code branches on DS:34E0 (object id):
#   * 0x0353 receives the special wide dog hit-test.
#   * 0x0321..0x0383 and 0x1389 use the large/multi-hit enemy path.
#   * 0x0072 and 0x0065 have their own object-specific hit paths.
#   * bank-14 guards are handled by their lower behaviour states/degrade path.
# Static shooter/trap object ids 0x01D0/0x01D1/0x01E7/0x01EB are deliberately
# absent: they behave as solid indestructible map actors, not enemies to kill.
SHOOTABLE_OBJECT_ID_RANGES: tuple[tuple[int, int], ...] = ((0x0321, 0x0383),)
SHOOTABLE_OBJECT_IDS: frozenset[int] = frozenset({0x0353, 0x1389, 0x0072, 0x0065, SHARK_SWIMMER_OBJECT_ID})
INDESTRUCTIBLE_SOLID_ACTOR_STATES: frozenset[int] = frozenset({0x0A, 0x0B, 0x0C, 0x0D, 0x0F, 0x10, 0x11, 0x12})

def object_id_is_shootable(object_id: int) -> bool:
    if object_id in SHOOTABLE_OBJECT_IDS:
        return True
    return any(lo <= object_id <= hi for lo, hi in SHOOTABLE_OBJECT_ID_RANGES)

# Object-specific durability hints observed so far.  The EXE often keeps these
# in per-actor auxiliary fields/state rather than a single explicit HP table,
# but these values prevent the port from treating every moving actor as one-shot.
ACTOR_HP_BY_OBJECT_ID: dict[int, int] = {
    0x0353: 3,  # bank0 two-tile dog
    0x0321: 3,
    0x0331: 3,
    0x0345: 3,
    0x0065: 3,
    0x0075: 3,
    SHARK_SWIMMER_OBJECT_ID: 1,
}

# State 0x21 / object 0x0345 ceiling crawler fires only while active/on-screen
# and only when the player is underneath its column.  The projectile branch uses
# a vertical laser/spark family; in the decoded atlas this is bank 12 tiles
# 44..47.
CEILING_CRAWLER_CODE = 0x63
CEILING_LASER_PROJECTILE_BANK = 12
CEILING_LASER_PROJECTILE_TILES = (44, 45, 46, 47)

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


# Stationary shooter/trap actor states from the update dispatcher around
# SAM1:0x6B74..0x6D47.  The init table gives their object ids and a
# random(20)+55 timer.  The dispatcher checks same tile row + direction before
# calling projectile helper 0x5784 with speed=4.
STATIONARY_SHOOTER_DIRECTION: dict[int, int] = {
    0x52: 1,   # state 0x0A, object 0x01D0, bank4 tile 13
    0x51: -1,  # state 0x0B, object 0x01D1, bank4 tile 14
    0x3C: 1,   # state 0x0C, object 0x01E7, bank4 tile 36
    0x3D: -1,  # state 0x0D, object 0x01EB, bank4 tile 40
}

STATIONARY_SHOOTER_PROJECTILE: dict[int, tuple[int, int, int]] = {
    # object 0x01D6 -> bank4 tile 19, same visible sprite both directions
    0x52: (4, 19, 19),
    0x51: (4, 19, 19),
    # object 0x01E8 -> bank4 tile 37 for the right-facing variant,
    # object 0x01EC -> bank4 tile 41 for the left-facing variant.
    0x3C: (4, 37, 41),
    0x3D: (4, 37, 41),
}

STATIONARY_SHOOTER_SPAWN_X_OFFSET: dict[int, int] = {
    0x52: 8,
    0x51: -8,
    0x3C: 16,
    0x3D: -16,
}

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

# Timed beam/laser trap actors recovered from state 0x0F/0x10 dispatcher
# around SAM1:0x6E81..0x6FB0.  Raw 0x3B is the vertical bank-3 trap,
# raw 0x3E is the horizontal bank-3 trap.  Both start with object id 0x01B3,
# DS:34D8=0x1E, DS:34DA=random(0x1E), then once the timer reaches the
# period they set object id to:
#   state 0x0F: 0x01AD + ((34DA-34D8) >> 2)
#   state 0x10: 0x01B5 + ((34DA-34D8) >> 2)
# and reset at 0x2D ticks.
BEAM_VERTICAL_CODE = 0x3B
BEAM_HORIZONTAL_CODE = 0x3E
BEAM_PERIOD_TICKS = 0x1E
BEAM_CYCLE_TICKS = 0x2D
BEAM_VERTICAL_STATE = 0x0F
BEAM_HORIZONTAL_STATE = 0x10
BEAM_IDLE_OBJECT_ID = 0x01B3
BEAM_VERTICAL_VISUAL_BASE_ID = 0x01AD
BEAM_HORIZONTAL_VISUAL_BASE_ID = 0x01B5

def beam_initial_timer(code: int, x: int, y: int) -> int:
    return deterministic_actor_rng(code, x, y, salt=0xBE) % BEAM_PERIOD_TICKS

def beam_phase_for_timer(timer: int) -> int | None:
    if timer < BEAM_PERIOD_TICKS:
        return None
    return max(0, min(3, (timer - BEAM_PERIOD_TICKS) >> 2))

def beam_is_dangerous(timer: int) -> bool:
    return beam_phase_for_timer(timer) is not None
