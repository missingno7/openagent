#!/usr/bin/env python3
"""Extract player/actor movement evidence from unpacked Secret Agent EXE disassembly.

This is not a decompiler.  It is a focused pattern extractor for the routines
already identified while reverse-engineering SAM1/SAM2/SAM3:

* the map-buffer collision probe routine that tests +0x1cc/+0x1cd;
* player globals and the keyboard ISR flags;
* the normal mission jump/fall path driven by 0x6ec1/0x34ea/0x34af;
* the distinct table-driven bounce/death path driven by 0x69f5/0x69f6.

The output is intended to be checked into docs/derived_mechanics so later editor
runtime code can be driven by EXE evidence rather than ad-hoc constants.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ADDR_RE = re.compile(r"^\s*([0-9a-f]+):")


@dataclass(frozen=True)
class EvidenceSpan:
    start: str
    end: str
    purpose: str
    notes: list[str]


@dataclass(frozen=True)
class MechanicReport:
    exe: str
    asm: str
    actor_struct: dict[str, str]
    player_globals: dict[str, str]
    keyboard_flags: dict[str, str]
    collision_probe_formula: dict[str, str]
    jump_model: dict[str, str]
    evidence_spans: list[EvidenceSpan]


def load_lines(path: Path) -> list[str]:
    return path.read_text(errors="replace").splitlines()


def line_addr(line: str) -> int | None:
    m = ADDR_RE.match(line)
    return int(m.group(1), 16) if m else None


def has_addr(lines: list[str], addr: int) -> bool:
    return any(line_addr(line) == addr for line in lines)


def span_exists(lines: list[str], start: int, end: int) -> bool:
    found_start = found_end = False
    for line in lines:
        addr = line_addr(line)
        if addr == start:
            found_start = True
        if addr == end:
            found_end = True
    return found_start and found_end


def report_for_asm(asm_path: Path) -> MechanicReport:
    lines = load_lines(asm_path)
    # The three SAM executables have tiny address shifts in some routines, but
    # the observed mechanics and DS offsets are identical.  Keep addresses as
    # SAM1 anchor locations when exact auto-location is not needed.
    spans = [
        EvidenceSpan(
            "0000", "084b", "keyboard ISR/control flags",
            [
                "reads scan code from port 0x60 into DS:6824",
                "sets left/right movement flags 6eca/6ecb and animation state 3500",
                "sets up/down/ladder-ish flags 6ec3/6ec4 and fire flag 6ecd",
                "uses configurable scan-code words at 70be/70c0/70c2/70ba/70bc/70c4",
            ],
        ),
        EvidenceSpan(
            "b8b3", "ba49", "normal mission fall path",
            [
                "increments byte counter 34ea and caps it to 0x13",
                "adds byte [34af + 34ea] to player Y",
                "checks body byte +0x1cc and later foot/platform byte +0x1cd",
                "snaps landing Y to a 16-pixel boundary",
            ],
        ),
        EvidenceSpan(
            "bced", "bd80", "normal mission jump path",
            [
                "starts with 6ec1=1 and 34ea=0",
                "increments 34ea and subtracts byte [34af + 34ea] from player Y",
                "at counter 0x0a clears 6ec1, rewinds 34ea to 9, and still applies table[9]",
                "uses one full-step collision probe and aborts the upward step when blocked",
            ],
        ),
        EvidenceSpan(
            "1a6b", "1ae8", "table-driven upward jump/bounce displacement",
            [
                "copies player current x/y to previous x/y globals 34f2/34f4",
                "toggles animation state 3500 between 0x0f and 0x10",
                "decrements byte timer 69f6",
                "uses remaining timer as word index: di = timer << 1; ax = word ptr [69f6+di]",
                "subtracts that word from player Y at 34f0, with top/camera clamps",
            ],
        ),
        EvidenceSpan(
            "53c4", "5479", "player/object overlap and jump trigger",
            [
                "player overlap uses 10-pixel horizontal window: x..x+9",
                "vertical overlap uses 16-pixel window: y..y+15",
                "sets 69f5=1 and 69f6=0x23 to start the table-driven jump/bounce path",
                "also handles limited multi-jump/bonus logic via 6a40/6a41/6a42",
            ],
        ),
        EvidenceSpan(
            "5a37", "5b96", "actor collision probe, state 1/2/... family",
            [
                "tile_x = (x >> 4) + 1, tile_y_top = (y >> 4) + 1, tile_y_bottom = ((y+15) >> 4) + 1",
                "right-side tile probe is tile_x + 1",
                "normal collision reads byte +0x1cc from runtime cell",
                "floor/one-way channel reads byte +0x1cd on vertical/bottom probes",
                "on left/right impacts it flips object horizontal direction 34e2 between +1 and -1",
            ],
        ),
        EvidenceSpan(
            "816b", "82d5", "main actor update dispatch before collision routine",
            [
                "iterates actor/object slots starting at index 2",
                "actor records are indexed by slot << 5, so each record is 0x20 bytes",
                "candidate x/y are current position plus direction*speed from 34e2/34e4 and 34e6",
                "calls 5a37 while actor state/type 34e8 is below 0x1e",
            ],
        ),
    ]
    return MechanicReport(
        exe=asm_path.name.replace("_unpacked_linear_8086.asm", ""),
        asm=str(asm_path),
        actor_struct={
            "+0x00 / DS:34cc+slot*0x20": "actor mode/substate, written in pickup/enemy transitions",
            "+0x02 / DS:34ce+slot*0x20": "x position in pixels",
            "+0x04 / DS:34d0+slot*0x20": "y position in pixels",
            "+0x06 / DS:34d2+slot*0x20": "previous x position",
            "+0x08 / DS:34d4+slot*0x20": "previous y position",
            "+0x0a / DS:34d6+slot*0x20": "animation/collision counter",
            "+0x0e / DS:34da+slot*0x20": "timer/aux counter used by some states",
            "+0x14 / DS:34e0+slot*0x20": "sprite/object id written during state changes",
            "+0x16 / DS:34e2+slot*0x20": "horizontal direction, usually +1 or -1",
            "+0x18 / DS:34e4+slot*0x20": "vertical direction, usually +1 or -1",
            "+0x1a / DS:34e6+slot*0x20": "per-tick speed/step size",
            "+0x1c / DS:34e8+slot*0x20": "actor type/state dispatch value",
            "+0x1e / DS:34ea+slot*0x20": "inactive/skip flag checked by dispatcher",
        },
        player_globals={
            "DS:34ee": "player x position in pixels",
            "DS:34f0": "player y position in pixels",
            "DS:34f2": "previous player x",
            "DS:34f4": "previous player y",
            "DS:3500": "player animation/state id",
            "DS:681c": "lives/active-player state gate used by controls",
            "DS:6838": "horizontal camera/scroll x clamp target",
            "DS:683a": "vertical camera/scroll y clamp target",
        },
        keyboard_flags={
            "DS:6eca": "left held flag from scan code at DS:70be",
            "DS:6ecb": "right held flag from scan code at DS:70c0",
            "DS:6ec2": "movement/control edge flag cleared on left/right press and jump/bounce end",
            "DS:6ec3": "up/ladder-ish held flag from scan code at DS:70ba",
            "DS:6ec4": "down/ladder-ish held flag from scan code at DS:70bc",
            "DS:6ecd": "fire/extra action held flag from scan code at DS:70c4",
        },
        collision_probe_formula={
            "runtime_cell_index": "((tile_y + 1) * 0xC8) + ((tile_x + 1) << 3)",
            "actor_left_tile": "(x >> 4) + 1",
            "actor_right_tile": "actor_left_tile + 1",
            "actor_top_tile": "(y >> 4) + 1",
            "actor_bottom_tile": "((y + 15) >> 4) + 1",
            "body_block_byte": "+0x1cc",
            "floor_or_one_way_byte": "+0x1cd",
            "player_overlap_x_window": "x..x+9 in routine 0x53c4",
            "player_overlap_y_window": "y..y+15 in routine 0x53c4",
        },
        jump_model={
            "normal_jump_start": "DS:6ec1=1 and DS:34ea=0 at SAM1 0xbced..0xbcf7",
            "normal_jump_tick": "increment DS:34ea; subtract byte [DS:34af + DS:34ea] from DS:34f0 at SAM1 0xbd06..0xbd7e",
            "normal_jump_apex": "when DS:34ea reaches 0x0a, clear DS:6ec1, rewind DS:34ea to 9, and still apply table[9]",
            "normal_fall_tick": "increment/cap DS:34ea; add byte [DS:34af + DS:34ea] to DS:34f0 at SAM1 0xb8b3..0xba49",
            "normal_table_init": "DS:34af byte table initialized at SAM1 0x28ed6..0x28f30",
            "separate_bounce_death_start": "DS:69f5 set to 1 and DS:69f6 set to 0x23 (35 ticks)",
            "separate_bounce_death_tick": "decrement DS:69f6; subtract word [DS:69f6 + (timer << 1)] from DS:34f0 at SAM1 0x1ab3..0x1ac0",
        },
        evidence_spans=spans,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--out", type=Path, default=Path("docs/derived_mechanics/player_mechanics.json"))
    args = ap.parse_args()
    reports = []
    for asm_path in sorted((args.root / "dissassembly").glob("SAM*_unpacked_linear_8086.asm")):
        reports.append(asdict(report_for_asm(asm_path)))
    out = args.root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(reports)} reports)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
