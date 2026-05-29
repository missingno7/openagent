#!/usr/bin/env python3
"""Extract pickup/score-popup mechanics from the unpacked Secret Agent EXE.

The interaction dispatcher reads the runtime cell visual id at +0x1CA, compares
it against object ids, optionally adds to the score dword at DS:699A, clears the
runtime cell, and calls helper 0x55F0 to spawn the flying score sprite.  The
helper receives a one-based bank-10 tile number, so 0x11 means decoded bank 10
sprite 16 ("100"), 0x12 means sprite 17 ("250"), etc.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from openagent.exe_runtime_collision import RUNTIME_CELL_WRITES

ADDR_RE = re.compile(r"^\s*([0-9a-f]+):")
CMP_RE = re.compile(r"cmp\s+\$0x([0-9a-f]+),%ax")
ADD_RE = re.compile(r"add\s+\$0x([0-9a-f]+),%ax")
MOV_AX_RE = re.compile(r"mov\s+\$0x([0-9a-f]+),%ax")


def line_addr(line: str) -> int | None:
    m = ADDR_RE.match(line)
    return int(m.group(1), 16) if m else None


def raw_codes_for_visual_id(visual_id: int) -> list[int]:
    codes: list[int] = []
    for code, writes in RUNTIME_CELL_WRITES.items():
        if any(w.cA == visual_id for w in writes):
            codes.append(code)
    return sorted(set(codes))


@dataclass(frozen=True)
class ScorePickupBranch:
    address: str
    runtime_visual_id: str
    raw_codes: list[str]
    score_delta: int
    popup_call_argument: int
    bank10_tile_zero_based: int
    evidence: list[str]


@dataclass(frozen=True)
class PickupReport:
    exe: str
    score_storage: str
    popup_helper: str
    notes: list[str]
    score_pickups: list[ScorePickupBranch]


def extract_score_branches(asm_path: Path) -> PickupReport:
    lines = asm_path.read_text(errors="replace").splitlines()
    out: list[ScorePickupBranch] = []
    seen: set[tuple[int, int, int]] = set()
    for i, line in enumerate(lines):
        m = CMP_RE.search(line)
        if not m:
            continue
        visual_id = int(m.group(1), 16)
        # Limit to the current cmp branch.  The dispatcher is a long
        # cmp/jne chain, so a fixed 90-line window can accidentally include
        # the next item branch.
        end = min(len(lines), i + 90)
        for j in range(i + 1, end):
            if CMP_RE.search(lines[j]):
                end = j
                break
        window = lines[i:end]
        text = "\n".join(window)
        if "0x699a" not in text or "call   0x55f0" not in text:
            continue
        # Make sure this branch really adds to score, not another counter such as ammo.
        les_index = next((j for j, l in enumerate(window) if "les" in l and "0x699a" in l), None)
        if les_index is None:
            continue
        value = None
        for l in window[les_index:les_index + 8]:
            am = ADD_RE.search(l)
            if am:
                value = int(am.group(1), 16)
                break
        if value is None:
            continue
        call_index = next((j for j, l in enumerate(window) if "call   0x55f0" in l), None)
        if call_index is None:
            continue
        popup_arg = None
        for l in reversed(window[max(0, call_index - 8):call_index]):
            mm = MOV_AX_RE.search(l)
            if mm:
                popup_arg = int(mm.group(1), 16)
                break
        if popup_arg is None:
            continue
        key = (visual_id, value, popup_arg)
        if key in seen:
            continue
        seen.add(key)
        addr = line_addr(line) or 0
        raw_codes = raw_codes_for_visual_id(visual_id)
        out.append(ScorePickupBranch(
            address=f"0x{addr:04x}",
            runtime_visual_id=f"0x{visual_id:04x}",
            raw_codes=[f"0x{c:02x}" for c in raw_codes],
            score_delta=value,
            popup_call_argument=popup_arg,
            bank10_tile_zero_based=popup_arg - 1,
            evidence=[l.strip() for l in window[: min(len(window), call_index + 2)] if l.strip()],
        ))
    return PickupReport(
        exe=asm_path.name.replace("_unpacked_linear_8086.asm", ""),
        score_storage="DS:699A/699C far/dword-like score accumulator; branches add constants such as 0x64, 0xFA, 0x1F4, 0x3E8.",
        popup_helper="near call 0x55F0; argument is one-based bank-10 score sprite number, so 0x11 -> tile 16, 0x12 -> tile 17, ...",
        notes=[
            "Interaction code clears runtime cell +0x1CA after pickup and sets redraw flag DS:6832=-1.",
            "Decoded bank 10 tiles 16..22 display 100, 250, 500, 1000, 2K, 5K, 10K.",
        ],
        score_pickups=out,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--out", type=Path, default=Path("docs/derived_mechanics/pickup_mechanics.json"))
    args = ap.parse_args()
    reports = []
    for asm in sorted((args.root / "dissassembly").glob("SAM*_unpacked_linear_8086.asm")):
        reports.append(asdict(extract_score_branches(asm)))
    out = args.root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(reports)} reports)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
