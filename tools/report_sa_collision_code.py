from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openagent.exe_runtime_collision import RUNTIME_CELL_WRITES, RuntimeCellWrite


def parse_code(text: str) -> int:
    return int(text, 16 if text.lower().startswith("0x") else 16)


def visible_ids(w: RuntimeCellWrite) -> list[int]:
    return [v for v in (w.c6, w.c8, w.cA) if v not in (0, 0x0002, 0x681A, 0xFFFF)]


def code_report(code: int) -> str:
    lines = [f"map byte 0x{code:02X}"]
    writes = RUNTIME_CELL_WRITES.get(code, ())
    if not writes:
        return f"map byte 0x{code:02X}: no EXE-derived runtime writes"
    for i, w in enumerate(writes, 1):
        ids = ", ".join(f"0x{v:04X}" for v in visible_ids(w)) or "-"
        lines.append(
            f"  {i}: dx={w.dx:+d} dy={w.dy:+d} body={int(w.body_solid)} foot={int(w.foot_solid)} "
            f"c6=0x{w.c6:04X} c8=0x{w.c8:04X} cA=0x{w.cA:04X} visual={ids} ctx={w.context} bg_only={w.requires_bg_row}"
        )
    return "\n".join(lines)


def find_visual_alias(visual_low: int) -> list[tuple[int, RuntimeCellWrite, int]]:
    hits=[]
    for code, writes in RUNTIME_CELL_WRITES.items():
        for w in writes:
            for v in visible_ids(w):
                if (v & 0xff) == visual_low:
                    hits.append((code, w, v))
    return hits


def main():
    p=argparse.ArgumentParser(description="Report EXE-derived collision writes for Secret Agent map bytes or displayed visual tile ids.")
    p.add_argument("codes", nargs="+", help="hex map bytes or displayed low-byte tile ids, e.g. D2 D3 70")
    p.add_argument("--visual", action="store_true", help="interpret arguments as low byte of displayed visual sprite ids instead of raw map bytes")
    ns=p.parse_args()
    for s in ns.codes:
        code=parse_code(s)
        if ns.visual:
            print(f"visual low byte 0x{code:02X}")
            hits=find_visual_alias(code)
            if not hits:
                print("  no visual-id alias in EXE collision writes")
            for src,w,v in hits:
                print(f"  drawn by map byte 0x{src:02X} via visual 0x{v:04X}: dx={w.dx:+d} dy={w.dy:+d} body={int(w.body_solid)} foot={int(w.foot_solid)}")
        else:
            print(code_report(code))
        print()

if __name__ == "__main__":
    main()
