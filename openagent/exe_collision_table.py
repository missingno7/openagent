from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ExeCollisionEntry:
    token_hex: str
    token_display: str
    internal_code: str
    layer_b: str
    layer_c: str
    body_solid: bool
    foot_solid: bool
    target_x: str
    target_y: str

# Generated from tools/extract_sa_collision_table.py, SAM1_unlz.exe.
# SAM2/SAM3 have the same token semantics; variable addresses differ.
SAMLEV_TOKEN_COLLISION: dict[int, tuple[ExeCollisionEntry, ...]] = {
    0x30: (
        ExeCollisionEntry('01 30', '\\x010', '0x020D', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x41: (
        ExeCollisionEntry('01 41', '\\x01A', '0x01F5', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x42: (
        ExeCollisionEntry('01 42', '\\x01B', '0x01F6', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x43: (
        ExeCollisionEntry('01 43', '\\x01C', '0x01F7', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x44: (
        ExeCollisionEntry('01 44', '\\x01D', '0x01F8', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x45: (
        ExeCollisionEntry('01 45', '\\x01E', '0x01F9', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x46: (
        ExeCollisionEntry('01 46', '\\x01F', '0x01FA', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x47: (
        ExeCollisionEntry('01 47', '\\x01G', '0x01FB', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x48: (
        ExeCollisionEntry('01 48', '\\x01H', 'word_681a', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x49: (
        ExeCollisionEntry('01 49', '\\x01I', 'word_681a', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x4A: (
        ExeCollisionEntry('01 4a', '\\x01J', '0x0295', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x4B: (
        ExeCollisionEntry('01 4b', '\\x01K', 'word_681a', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x4C: (
        ExeCollisionEntry('01 4c', '\\x01L', 'word_681a', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x4D: (
        ExeCollisionEntry('01 4d', '\\x01M', '?', '0x00', '0x0205', False, False, 'x', 'y'),
        ExeCollisionEntry('01 4d', '\\x01M', '?', '0x00', '0x0201', False, False, 'x', 'y'),
    ),
    0x4E: (
        ExeCollisionEntry('01 4e', '\\x01N', '?', '0x00', '0x0206', False, False, 'x', 'y'),
        ExeCollisionEntry('01 4e', '\\x01N', '?', '0x00', '0x0202', False, False, 'x', 'y'),
    ),
    0x4F: (
        ExeCollisionEntry('01 4f', '\\x01O', '?', '0x00', '0x0207', False, False, 'x', 'y'),
        ExeCollisionEntry('01 4f', '\\x01O', '?', '0x00', '0x0203', False, False, 'x', 'y'),
    ),
    0x50: (
        ExeCollisionEntry('01 50', '\\x01P', '?', '0x00', '0x0208', False, False, 'x', 'y'),
        ExeCollisionEntry('01 50', '\\x01P', '?', '0x00', '0x0204', False, False, 'x', 'y'),
    ),
    0x51: (
        ExeCollisionEntry('01 51', '\\x01Q', '0x0205', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x52: (
        ExeCollisionEntry('01 52', '\\x01R', '0x0206', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x53: (
        ExeCollisionEntry('01 53', '\\x01S', '0x0207', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x54: (
        ExeCollisionEntry('01 54', '\\x01T', '0x0208', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x55: (
        ExeCollisionEntry('01 55', '\\x01U', '0x0209', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x56: (
        ExeCollisionEntry('01 56', '\\x01V', '0x020A', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x57: (
        ExeCollisionEntry('01 57', '\\x01W', '0x020B', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x58: (
        ExeCollisionEntry('01 58', '\\x01X', '0x020C', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x5A: (
        ExeCollisionEntry('01 5a', '\\x01Z', '0x020E', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x61: (
        ExeCollisionEntry('01 61', '\\x01a', '0x020F', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x62: (
        ExeCollisionEntry('01 62', '\\x01b', '0x0210', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x63: (
        ExeCollisionEntry('01 63', '\\x01c', '0x0211', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x64: (
        ExeCollisionEntry('01 64', '\\x01d', '0x0212', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x65: (
        ExeCollisionEntry('01 65', '\\x01e', '0x0213', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x66: (
        ExeCollisionEntry('01 66', '\\x01f', '0x0214', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x67: (
        ExeCollisionEntry('01 67', '\\x01g', '0x0215', '0x00', '0x00', True, False, 'x', 'y'),
    ),
    0x68: (
        ExeCollisionEntry('01 68', '\\x01h', '0x0216', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x69: (
        ExeCollisionEntry('01 69', '\\x01i', '0x0217', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x6A: (
        ExeCollisionEntry('01 6a', '\\x01j', '0x0218', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x6B: (
        ExeCollisionEntry('01 6b', '\\x01k', '0x0219', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x6C: (
        ExeCollisionEntry('01 6c', '\\x01l', '0x01FC', '0x00', '0x00', True, False, 'x', 'y'),
        ExeCollisionEntry('01 6c', '\\x01l', 'word_681a', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x6D: (
        ExeCollisionEntry('01 6d', '\\x01m', 'word_681a', '0x00', '0x0299', False, False, 'x', 'y'),
    ),
    0x6E: (
        ExeCollisionEntry('01 6e', '\\x01n', 'word_681a', '0x00', '0x029A', False, False, 'x', 'y'),
    ),
    0x6F: (
        ExeCollisionEntry('01 6f', '\\x01o', 'word_681a', '0x029F', '0x00', False, True, 'x', 'y'),
    ),
    0x70: (
        ExeCollisionEntry('01 70', '\\x01p', 'word_681a', '0x02A0', '0x00', False, True, 'x', 'y'),
    ),
    0x71: (
        ExeCollisionEntry('01 71', '\\x01q', 'word_681a', '0x02A1', '0x00', False, True, 'x', 'y'),
    ),
    0x72: (
        ExeCollisionEntry('01 72', '\\x01r', 'word_681a', '0x02A2', '0x00', False, True, 'x', 'y'),
    ),
    0x73: (
        ExeCollisionEntry('01 73', '\\x01s', '0x02AB', '0x00', '0x00', False, False, 'x', 'y'),
    ),
    0x74: (
        ExeCollisionEntry('01 74', '\\x01t', 'word_681a', '0x00', '0x02AC', False, False, 'x', 'y'),
    ),
    0x75: (
        ExeCollisionEntry('01 75', '\\x01u', 'word_681a', '0x00', '0x02AD', False, False, 'x', 'y'),
    ),
    0x76: (
        ExeCollisionEntry('01 76', '\\x01v', 'word_681a', '0x00', '0x02AE', False, False, 'x', 'y'),
    ),
    0x77: (
        ExeCollisionEntry('01 77', '\\x01w', 'word_681a', '0x00', '0x02AF', False, False, 'x', 'y'),
        ExeCollisionEntry('01 77', '\\x01w', '0x02', '0x00', '0xB3', True, False, 'x-1', 'y'),
        ExeCollisionEntry('01 77', '\\x01w', '0x02', '0x00', '0xB7', False, False, 'x', 'y'),
    ),
    0x78: (
        ExeCollisionEntry('01 78', '\\x01x', 'word_681a', '0x00', '0x02B0', False, False, 'x', 'y'),
    ),
    0x79: (
        ExeCollisionEntry('01 79', '\\x01y', 'word_681a', '0x00', '0x02B1', False, False, 'x', 'y'),
    ),
    0x7A: (
        ExeCollisionEntry('01 7a', '\\x01z', '0x02B2', '0x00', '0x00', False, False, 'x', 'y'),
    ),
}

def token_has_body_solid(token_second_byte: int) -> bool:
    return any(e.body_solid for e in SAMLEV_TOKEN_COLLISION.get(token_second_byte, ()))

def token_has_foot_solid(token_second_byte: int) -> bool:
    return any(e.foot_solid for e in SAMLEV_TOKEN_COLLISION.get(token_second_byte, ()))
