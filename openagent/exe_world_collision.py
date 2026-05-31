from __future__ import annotations
from .exe_runtime_collision import RuntimeCellWrite

# Generated from docs/derived_collision_tables_all/SAM1_runtime_collision_calls.json.
# This is the level-0 / overworld parser branch selected by SAM1:0x10811
# when DS:681C == 1.  Do not use the mission parser table for level 0.

WORLD_RUNTIME_CELL_WRITES: dict[int, tuple[RuntimeCellWrite, ...]] = {
    0x30: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x020D, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x41: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x01F5, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x42: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x01F6, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x43: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x01F7, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x44: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x01F8, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x45: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x01F9, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x46: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x01FA, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x47: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x01FB, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x48: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x49: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x4A: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0295, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x4B: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x4C: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x4D: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0000, c8=0x0000, cA=0x0205, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
        RuntimeCellWrite(dx=0, dy=0, c6=0x0000, c8=0x0000, cA=0x0201, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x4E: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0000, c8=0x0000, cA=0x0206, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
        RuntimeCellWrite(dx=0, dy=0, c6=0x0000, c8=0x0000, cA=0x0202, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x4F: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0000, c8=0x0000, cA=0x0207, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
        RuntimeCellWrite(dx=0, dy=0, c6=0x0000, c8=0x0000, cA=0x0203, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x50: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0000, c8=0x0000, cA=0x0208, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
        RuntimeCellWrite(dx=0, dy=0, c6=0x0000, c8=0x0000, cA=0x0204, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x51: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0205, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x52: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0206, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x53: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0207, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x54: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0208, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x55: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0209, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x56: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x020A, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x57: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x020B, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x58: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x020C, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x5A: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x020E, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x61: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x020F, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x62: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0210, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x63: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0211, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x64: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0212, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x65: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0213, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x66: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0214, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x67: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0215, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x68: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0216, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x69: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0217, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x6A: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0218, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x6B: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x0219, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x6C: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x01FC, c8=0x0000, cA=0x0000, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x6D: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x0299, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x6E: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x029A, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x6F: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x029F, cA=0x0000, body_solid=False, foot_solid=True, context='world_main', requires_bg_row=True),
    ),
    0x70: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x02A0, cA=0x0000, body_solid=False, foot_solid=True, context='world_main', requires_bg_row=True),
    ),
    0x71: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x02A1, cA=0x0000, body_solid=False, foot_solid=True, context='world_main', requires_bg_row=True),
    ),
    0x72: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x02A2, cA=0x0000, body_solid=False, foot_solid=True, context='world_main', requires_bg_row=True),
    ),
    0x73: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x02AB, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x74: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x02AC, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x75: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x02AD, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x76: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x02AE, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x77: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x02AF, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
        RuntimeCellWrite(dx=0, dy=-1, c6=0x0002, c8=0x0000, cA=0x00B3, body_solid=True, foot_solid=False, context='world_main', requires_bg_row=True),
        RuntimeCellWrite(dx=0, dy=0, c6=0x0002, c8=0x0000, cA=0x00B7, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x78: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x02B0, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x79: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x681A, c8=0x0000, cA=0x02B1, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
    0x7A: (
        RuntimeCellWrite(dx=0, dy=0, c6=0x02B2, c8=0x0000, cA=0x0000, body_solid=False, foot_solid=False, context='world_main', requires_bg_row=True),
    ),
}

WORLD_BODY_SOLID_CODES = frozenset({
    0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x55, 0x61, 0x66, 0x67, 0x6C, 0x77,
})

WORLD_FOOT_SOLID_CODES = frozenset({
    0x6F, 0x70, 0x71, 0x72,
})

KNOWN_WORLD_RUNTIME_CODES = frozenset({
    0x30, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x4B,
    0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57,
    0x58, 0x5A, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A,
    0x6B, 0x6C, 0x6D, 0x6E, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76,
    0x77, 0x78, 0x79, 0x7A,
})

def world_runtime_cell_writes_for_code(code: int) -> tuple[RuntimeCellWrite, ...]:
    return WORLD_RUNTIME_CELL_WRITES.get(code, ())
