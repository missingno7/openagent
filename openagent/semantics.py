from __future__ import annotations

from dataclasses import dataclass


WORLD_PLAYER_CODE = 0x59
WORLD_ENTRANCE_CODES = frozenset({0x4D, 0x4F, 0x50})
MISSION_PLAYER_START_CODE = 0x59

# World-map codes use a different table from mission levels. Grass/path tiles
# are deliberately omitted: they are walkable on the island map.
WORLD_WATER_CODES = frozenset({0x55})
WORLD_COAST_CODES = frozenset({0x56, 0x57, 0x58, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68})
WORLD_TREE_CODES = frozenset({0x42, 0x43, 0x44, 0x45, 0x46, 0x47})
WORLD_BLOCKED_CODES = frozenset({0x00, 0x20}) | WORLD_WATER_CODES | WORLD_COAST_CODES | WORLD_TREE_CODES
MOVING_PLATFORM_CODE = 0x62
RIDING_ENEMY_CODE = 0x65


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
    0xA7: CodeSemantics(
        "pushable",
        "pushable barrel",
        "User hint plus manual string 'Pushable barrel.' in all three extracted string files.",
        bank=6,
        tile=24,
    ),
    0x73: CodeSemantics(
        "ammo",
        "extra shots",
        "User hint plus manual string 'Extra shots' in all three extracted string files.",
        bank=9,
        tile=0,
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
    if semantics.kind in {"player_start", "moving_platform", "enemy", "score_item", "ammo", "key"}
)

# These are map/environment bytes that the executable/render tables and level
# data prove cannot behave like solid wall blocks. Codes 0x1E, 0x99, and 0xBE
# appear directly underneath valid 0x59 start markers; 0x35-0x37 are background
# shade variants handled specially by the original draw code.
MISSION_PASSABLE_ENV_CODES = frozenset({0x1E, 0x35, 0x36, 0x37, 0x99, 0xBE})
MISSION_PASSABLE_CODES = MISSION_PASSABLE_OBJECT_CODES | MISSION_PASSABLE_ENV_CODES


def is_mission_code_solid(code: int) -> bool:
    if code in (0, 0x20, ord("*")):
        return False
    return code not in MISSION_PASSABLE_CODES
