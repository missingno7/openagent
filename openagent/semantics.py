from __future__ import annotations

from dataclasses import dataclass

from .exe_runtime_collision import (
    code_has_body_solid as exe_code_has_body_solid,
    code_has_foot_solid as exe_code_has_foot_solid,
    code_known_to_exe_collision_table,
)


WORLD_PLAYER_CODE = 0x59
WORLD_ENTRANCE_CODES = frozenset({0x4D, 0x4E, 0x4F, 0x50})
MISSION_PLAYER_START_CODE = 0x59
WATER_CODE = 0x60
# Runtime object visuals that immediately route to the player-death branch in
# the EXE interaction dispatcher (SAM1:0xD221..0xD254).  The raw level bytes
# that write these cA values include water 0x60 and several other hard hazards.
HARD_DEATH_RUNTIME_VISUAL_IDS = frozenset({0x01F3, 0x025B, 0x0265, 0x0267, 0x0268})

# World-map codes use a different table from mission levels.  Do not infer
# overworld collision from visual raw-code families: pass 98 traces movement to
# the runtime collision byte +0x1CC, sampled at the 10x16 player-origin rect.
MOVING_PLATFORM_CODE = 0x62
ROTATING_SATELLITE_CODE = 0x23
PUSHABLE_BARREL_CODE = 0xA7
RIDING_ENEMY_CODE = 0x65
WALKER_ENEMY_CODES = frozenset({0x65, 0x6E, 0x75, 0x76, 0x7F, 0x5F, 0x6D})
# Multi-tile actors recovered from the same EXE special actor table.  They are
# not static composite scenery; the object id lives in DS:34E0 and the actor
# update branch moves/animates them.
MULTI_TILE_ACTOR_CODES = frozenset({0xAE, 0x24, 0x56, 0x58, 0x63})
# Stationary shooter traps recovered from actor states 0x0A..0x0D.
# 0x52/0x3C face right, 0x51/0x3D face left; they fire only when the
# player is on the same 16px row and in front of the emitter.
STATIONARY_SHOOTER_CODES = frozenset({0x52, 0x51, 0x3C, 0x3D})
FLOOR_SPIKE_CODE = 0x3F
CEILING_SPIKE_CODE = 0x41
SPIKE_TRAP_CODES = frozenset({FLOOR_SPIKE_CODE, CEILING_SPIKE_CODE})
BEAM_VERTICAL_CODE = 0x3B
BEAM_HORIZONTAL_CODE = 0x3E
BEAM_TRAP_CODES = frozenset({BEAM_VERTICAL_CODE, BEAM_HORIZONTAL_CODE})
LASER_FIELD_CODE = 0x82
LASER_COMPUTER_CODE = 0x83
FLOPPY_DISK_CODE = 0x84
DYNAMITE_CODE = 0x74
EXIT_DOOR_CODE = 0x71
EXIT_DOOR_RUNTIME_VISUAL = 0x027D
EXIT_DOOR_OPEN_RUNTIME_VISUAL = 0x027E
TELEPORTER_CODE = 0x77
TELEPORT_RUNTIME_VISUAL = 0x00B7
# Bank-14 human guard family.  These raw map bytes are not normal static
# sprites: the EXE special-low actor table creates actor records for them and
# the active sprite lives in actor field DS:34E0, not in the runtime cell.
# Atlas relation recovered from TILE_MAP/bank 14:
#   0x38 -> tile 0, 0x39 -> tile 8, 0x30 -> tile 16,
#   0x67 -> tile 24, 0x47 -> tile 32.
# The two stronger variants shoot; hits degrade base_tile by 8 until tile 0,
# then create the RIP object at tile 40.
BANK14_GUARD_INFO: dict[int, dict[str, int | bool]] = {
    0x38: {"base_tile": 0, "shoots": False},
    0x39: {"base_tile": 8, "shoots": False},
    0x30: {"base_tile": 16, "shoots": False},
    0x67: {"base_tile": 24, "shoots": True},
    0x47: {"base_tile": 32, "shoots": True},
}
BANK14_GUARD_CODES = frozenset(BANK14_GUARD_INFO)
BANK14_GUARD_CODE_BY_BASE_TILE = {int(v["base_tile"]): k for k, v in BANK14_GUARD_INFO.items()}
BANK14_RIP_TILE = 40
BANK14_RIP_SHOT_SCORE = 500
# User-verified against the original game: collecting the bank-14 grave/RIP
# object is a 1000-point pickup. Earlier EXE pass over-read nearby 0x61A8
# score logic from a different branch and made the popup fall back to 10K.
BANK14_RIP_PICKUP_SCORE = 1000
GLASSES_CODE = 0x72
SPEED_BONUS_CODE = 0x4E
HIDDEN_PLATFORM_CODE = 0xD3
ACTIVE_HIDDEN_PLATFORM_COLLISION_CODE = 0xD7

# Score pickup mechanics recovered from the EXE interaction dispatcher.  The
# runtime cell's +0x1CA visual id is compared against constants such as 0x25D,
# 0x26A..0x26F, then the EXE adds the shown amount to DS:699A and calls the
# small popup-spawn helper 0x55F0 with a one-based bank-10 tile id.  The values
# here are keyed by raw SAM?03.GFX map byte after inverting the executable's
# generated runtime-cell table.
SCORE_POPUP_TILE_BY_VALUE = {
    100: 16,
    250: 17,
    500: 18,
    1000: 19,
    2000: 20,
    5000: 21,
    10000: 22,
}
EXE_SCORE_PICKUP_VALUES: dict[int, int] = {
    0x01: 1000,
    0x4B: 500,
    0x4E: 250,
    0x50: 2000,
    0x54: 1000,
    0x57: 250,
    0x5B: 1000,  # historical/static fallback; runtime state 0x29 actor awards 5000
    0x5C: 500,
    0x5D: 100,
    0x64: 1000,
    0x66: 500,
    0x68: 100,
    0x74: 500,
    0x84: 500,
    0x8C: 100,
    0x8D: 100,
    0x8E: 10000,
}


@dataclass(frozen=True)
class CodeSemantics:
    kind: str
    name: str
    source: str
    bank: int | None = None
    tile: int | None = None
    unlocks: int | None = None
    key_code: int | None = None


MISSION_CODE_SEMANTICS: dict[int, CodeSemantics] = {
    0x59: CodeSemantics(
        "player_start",
        "player start",
        "User hint; appears in every raw world/mission block, with one known duplicate in episode 3 level 3; EXE writes literal 0x59 in all three SAM binaries.",
        bank=13,
        tile=0,
    ),
    MOVING_PLATFORM_CODE: CodeSemantics(
        "moving_platform",
        "moving platform",
        "User hint; atlas shows a platform; EXE writes literal 0x62 in all three SAM binaries.",
        bank=6,
        tile=25,
    ),
    RIDING_ENEMY_CODE: CodeSemantics(
        "enemy",
        "riding enemy",
        "User hint; atlas shows a small enemy; EXE compares/writes literal 0x65 in all three SAM binaries.",
        bank=2,
        tile=16,
    ),
    0x6D: CodeSemantics(
        "enemy",
        "fire walker",
        "Raw 0x6D is the bank-3 44..47 fire actor: a live horizontal contact hazard, not a projectile-damage target.",
        bank=3,
        tile=44,
    ),
    0x5B: CodeSemantics(
        "score_item",
        "money bag",
        "User hint plus manual string 'Money bag.' in all three extracted string files.",
        bank=5,
        tile=18,
    ),
    0x84: CodeSemantics(
        "score_item",
        "score pickup",
        "User hint plus repeated data occurrences; exact score value still needs EXE recovery.",
        bank=5,
        tile=4,
    ),

    TELEPORTER_CODE: CodeSemantics(
        "teleporter",
        "paired teleporter",
        "EXE interaction dispatcher SAM1:0xD48B compares runtime visual 0x00B7, plays sound 0x17, scans the runtime map for a second 0x00B7, then warps through DS:69E0/69E2/69E4/69E6.",
        bank=10,
        tile=32,
    ),
    0xA7: CodeSemantics(
        "pushable",
        "pushable barrel",
        "User hint plus manual string 'Pushable barrel.' in all three extracted string files.",
        bank=6,
        tile=24,
    ),

    DYNAMITE_CODE: CodeSemantics(
        "dynamite",
        "dynamite",
        "EXE interaction dispatcher: runtime visual 0x027B sets DS:69F4=1, clears the cell, plays sound 0x05, awards 500 points with popup arg 0x13.",
        bank=10,
        tile=28,
    ),
    EXIT_DOOR_CODE: CodeSemantics(
        "exit_door",
        "level exit door",
        "Raw 0x71 writes runtime visuals 0x0279/0x027D. Touching 0x027D with DS:69F4 dynamite set consumes it, plays sound 0x0B and spawns object 0x027B/state 0x16; when the blast timer completes the actor branch rewrites lower visual 0x027D to passable 0x027E and rewrites the upper 0x0279 cell to layer-B visual 0x027A, clearing collision for both rather than deleting the door.",
        bank=10,
        tile=29,
    ),
    0x73: CodeSemantics(
        "ammo",
        "extra shots",
        "User hint plus manual string 'Extra shots' in all three extracted string files.",
        bank=9,
        tile=0,
    ),
    GLASSES_CODE: CodeSemantics(
        "glasses",
        "x-ray glasses / reveal glasses",
        "EXE compares the object visual id against 0x0272 and takes a special drawing/mechanic branch; atlas maps raw 0x72 to bank 5 tile 6.",
        bank=5,
        tile=6,
    ),
    0x2B: CodeSemantics(
        "key",
        "green key",
        "User hint plus manual string 'Keys match colored doors.' in all three extracted string files.",
        bank=3,
        tile=20,
        unlocks=0x2C,
    ),
    0x2C: CodeSemantics(
        "door",
        "green door",
        "User hint plus manual string 'Keys match colored doors.' in all three extracted string files.",
        bank=3,
        tile=21,
        key_code=0x2B,
    ),
    0x2D: CodeSemantics(
        "key",
        "red key",
        "User hint plus manual string 'Keys match colored doors.' in all three extracted string files.",
        bank=3,
        tile=22,
        unlocks=0x2E,
    ),
    0x2E: CodeSemantics(
        "door",
        "red door",
        "User hint plus manual string 'Keys match colored doors.' in all three extracted string files.",
        bank=3,
        tile=23,
        key_code=0x2D,
    ),
    0x2F: CodeSemantics(
        "key",
        "blue key",
        "User hint plus manual string 'Keys match colored doors.' in all three extracted string files.",
        bank=3,
        tile=24,
        unlocks=0x34,
    ),
    0x34: CodeSemantics(
        "door",
        "blue door",
        "User hint plus manual string 'Keys match colored doors.' in all three extracted string files.",
        bank=3,
        tile=25,
        key_code=0x2F,
    ),
}

MISSION_PASSABLE_OBJECT_CODES = frozenset(
    code
    for code, semantics in MISSION_CODE_SEMANTICS.items()
    if semantics.kind in {"player_start", "moving_platform", "enemy", "score_item", "ammo", "key", "dynamite"}
)

# Runtime collision is now derived from the executable's map-token -> runtime-cell
# setter calls.  Keep the older semantic names for UI/collectibles, but do not
# drive wall/passability from hand-written visual guesses.
MISSION_PASSABLE_ENV_CODES = frozenset()
MISSION_ONE_WAY_PLATFORM_CODES = frozenset(
    code for code in range(256)
    if code_known_to_exe_collision_table(code)
    and exe_code_has_foot_solid(code)
    and not exe_code_has_body_solid(code)
)
MISSION_PASSABLE_CODES = frozenset(
    code for code in range(256)
    if code_known_to_exe_collision_table(code)
    and not exe_code_has_body_solid(code)
)
ANIMATED_SPECIAL_CODES = frozenset({0x40, 0xD4, 0x78})
STATE17_LANDMINE_CODES = frozenset({0x4D})
STATE29_MONEY_BAG_DYNAMIC_CODES = frozenset({0x5B})
DYNAMIC_MISSION_CODES = frozenset({MISSION_PLAYER_START_CODE, MOVING_PLATFORM_CODE, ROTATING_SATELLITE_CODE, PUSHABLE_BARREL_CODE}) | WALKER_ENEMY_CODES | MULTI_TILE_ACTOR_CODES | STATIONARY_SHOOTER_CODES | BANK14_GUARD_CODES | SPIKE_TRAP_CODES | BEAM_TRAP_CODES | ANIMATED_SPECIAL_CODES | STATE29_MONEY_BAG_DYNAMIC_CODES | STATE17_LANDMINE_CODES


def mission_code_semantics(code: int) -> CodeSemantics | None:
    return MISSION_CODE_SEMANTICS.get(code)


def mission_code_kind(code: int) -> str | None:
    semantics = mission_code_semantics(code)
    return semantics.kind if semantics else None


def score_value_for_code(code: int) -> int | None:
    return EXE_SCORE_PICKUP_VALUES.get(code)


def score_popup_tile_for_value(value: int) -> int | None:
    return SCORE_POPUP_TILE_BY_VALUE.get(value)


def is_collectible_code(code: int) -> bool:
    return code in EXE_SCORE_PICKUP_VALUES or mission_code_kind(code) in {"score_item", "ammo", "key", "glasses", "dynamite"}


def is_door_code(code: int) -> bool:
    return mission_code_kind(code) == "door"


def is_exit_door_code(code: int) -> bool:
    return mission_code_kind(code) == "exit_door"


def door_unlocked_by(code: int) -> int | None:
    semantics = mission_code_semantics(code)
    return semantics.key_code if semantics and semantics.kind == "door" else None


def is_one_way_platform_code(code: int) -> bool:
    return code in MISSION_ONE_WAY_PLATFORM_CODES


def is_dynamic_mission_code(code: int) -> bool:
    return code in DYNAMIC_MISSION_CODES


def is_mission_code_body_solid(code: int) -> bool:
    if code in (0, 0x20, ord("*")):
        return False
    if code_known_to_exe_collision_table(code):
        return exe_code_has_body_solid(code)
    return True


def is_mission_code_floor_solid(code: int) -> bool:
    if code in (0, 0x20, ord("*")):
        return False
    if code_known_to_exe_collision_table(code):
        return exe_code_has_body_solid(code) or exe_code_has_foot_solid(code)
    return True


def is_mission_code_solid(code: int) -> bool:
    # Backwards-compatible name: normal body collision. Use
    # is_mission_code_floor_solid() for downward/floor probes.
    return is_mission_code_body_solid(code)
