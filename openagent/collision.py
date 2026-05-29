from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EDITOR_ROOT = ROOT / "secret_agent_editor"
if str(EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(EDITOR_ROOT))

from secret_agent_editor.constants import LEVEL_H, LEVEL_W, TILE


# Secret Agent keeps a padded runtime cell buffer. The disassembly indexes it as
# roughly:
#   cell = buffer + ((tile_x + 1) * 0xC8) + ((tile_y + 1) << 3)
# where 0xC8 is a column stride (25 padded Y cells * 8 bytes). Earlier project
# notes had this transposed; the corrected axis mapping is needed for composite
# one-way objects such as 0xD2. The engine tests byte +0x1CC for normal blocking
# and byte +0x1CD for some vertical/
# platform probes. In source coordinates we do not model the padded border, but
# we keep the same pixel probes and collision-channel split.
RUNTIME_CELL_STRIDE = 0xC8
RUNTIME_CELL_SIZE = 8
RUNTIME_CODE_A_OFFSET = 0x1C6
RUNTIME_CODE_B_OFFSET = 0x1C8
RUNTIME_CODE_C_OFFSET = 0x1CA
RUNTIME_SOLID_OFFSET = 0x1CC
RUNTIME_FOOT_OFFSET = 0x1CD

# The player sprite is 16x16, but the EXE does not collide with the full image.
# Routine around SAM1 0xB7D9 samples x+3/x+12 and y/y+15.
PLAYER_COLLISION_LEFT = 3
PLAYER_COLLISION_RIGHT = 12
PLAYER_COLLISION_TOP = 0
PLAYER_COLLISION_BOTTOM = 15
PLAYER_DRAW_W = 16
PLAYER_DRAW_H = 16


class CollisionChannel(str, Enum):
    BODY = "body"       # map-buffer byte +0x1cc in the original runtime
    FOOT = "foot"       # map-buffer byte +0x1cd in downward/floor probes


@dataclass(frozen=True)
class CollisionProbe:
    pixel_x: int
    pixel_y: int
    tile_x: int
    tile_y: int


def tile_coord(pixel: float) -> int:
    return int(pixel) // TILE


def player_body_probes(x: float, y: float, *, dx: float = 0.0, dy: float = 0.0) -> tuple[CollisionProbe, ...]:
    left = int(x + dx + PLAYER_COLLISION_LEFT)
    right = int(x + dx + PLAYER_COLLISION_RIGHT)
    top = int(y + dy + PLAYER_COLLISION_TOP)
    bottom = int(y + dy + PLAYER_COLLISION_BOTTOM)
    points = ((left, top), (right, top), (left, bottom), (right, bottom))
    return tuple(CollisionProbe(px, py, tile_coord(px), tile_coord(py)) for px, py in points)


def player_foot_probes(x: float, y: float, *, dy: float = 1.0) -> tuple[CollisionProbe, CollisionProbe]:
    py = int(y + PLAYER_COLLISION_BOTTOM + dy)
    left = int(x + PLAYER_COLLISION_LEFT)
    right = int(x + PLAYER_COLLISION_RIGHT)
    return (
        CollisionProbe(left, py, tile_coord(left), tile_coord(py)),
        CollisionProbe(right, py, tile_coord(right), tile_coord(py)),
    )


def in_level_bounds(tile_x: int, tile_y: int) -> bool:
    return 0 <= tile_x < LEVEL_W and 0 <= tile_y < LEVEL_H
