from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_asm(ep: int):
    path = ROOT / "dissassembly" / f"SAM{ep}_unpacked_linear_8086.asm"
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"\s*([0-9a-f]+):\s+[0-9a-f ]+\s+(.+)$", line)
        if m:
            rows.append((int(m.group(1), 16), m.group(2).strip(), line.rstrip()))
    return rows


def table_delta(ep: int, table_addr: int = 0x3A59) -> int:
    data = (ROOT / "dissassembly" / f"SAM{ep}_unlz.exe").read_bytes()
    marker = bytes([0x01, 0xAE, 0x01, 0x38, 0x01, 0x39, 0x01, 0x30, 0x01, 0x67, 0x01, 0x47])
    pos = data.find(marker)
    if pos < 0:
        raise RuntimeError(f"SAM{ep}: could not find special actor table bytes")
    return pos - table_addr


def find_cases(rows):
    cases = []
    for i, (addr, ins, _line) in enumerate(rows):
        m = re.match(r"mov\s+\$0x(3a[0-9a-f]+),%di", ins)
        if not m:
            continue
        if any("lcall  $0x2cd0,$0x724" in rows[j][1] for j in range(i, min(i + 8, len(rows)))):
            cases.append((i, addr, int(m.group(1), 16)))
    return cases


def imm_write(block, field: str):
    for _addr, ins, _line in block:
        m = re.search(rf"movw\s+\$0x([0-9a-f]+),0x{field}\(%di\)", ins)
        if m:
            return int(m.group(1), 16)
    return None


def detect_random_expr(block, field: str):
    """Find patterns random(n)+base written to actor field."""
    for idx, (_addr, ins, _line) in enumerate(block):
        if f"0x{field}(%di)" not in ins or not ins.startswith("mov"):
            continue
        # Look back for: mov $N,%ax; push %ax; lcall random; add $B,%ax
        text = "\n".join(row[1] for row in block[max(0, idx - 14): idx + 1])
        m = re.search(r"mov\s+\$0x([0-9a-f]+),%ax\n\s*push\s+%ax\n\s*lcall\s+\$0x2cd0,\$0x980\n\s*add\s+\$0x([0-9a-f]+),%ax", text)
        if m:
            return {"random_max_exclusive": int(m.group(1), 16), "add": int(m.group(2), 16)}
    return None


def has_random_direction(block):
    text = "\n".join(row[1] for row in block)
    return "mov    $0x2,%ax\npush   %ax\nlcall  $0x2cd0,$0x980" in text and "0x34e2(%di)" in text


def extract(ep: int):
    rows = parse_asm(ep)
    cases = find_cases(rows)
    data = (ROOT / "dissassembly" / f"SAM{ep}_unlz.exe").read_bytes()
    delta = table_delta(ep)
    out = []
    for n, (idx, addr, off) in enumerate(cases):
        next_idx = cases[n + 1][0] if n + 1 < len(cases) else min(idx + 300, len(rows))
        block = rows[idx:next_idx]
        tok = data[delta + off: delta + off + 2]
        if len(tok) != 2 or tok[0] != 1:
            continue
        record = {
            "token_offset": f"0x{off:04X}",
            "raw_code": tok[1],
            "raw_code_hex": f"0x{tok[1]:02X}",
            "case_addr": f"0x{addr:05X}",
            "object_id": imm_write(block, "34e0"),
            "object_id_hex": None,
            "step_px": imm_write(block, "34e6"),
            "behavior_state": imm_write(block, "34e8"),
            "timer_period": imm_write(block, "34d8"),
            "timer_period_random": detect_random_expr(block, "34d8"),
            "aux_dc": imm_write(block, "34dc"),
            "random_initial_direction": has_random_direction(block),
        }
        if record["object_id"] is not None:
            record["object_id_hex"] = f"0x{record['object_id']:04X}"
        out.append(record)
    return out


def main():
    out_dir = ROOT / "docs" / "derived_mechanics"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {f"SAM{ep}": extract(ep) for ep in (1, 2, 3)}
    out = out_dir / "pass18_special_actor_table.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    for rec in data["SAM1"]:
        if rec["raw_code"] in {0x38, 0x39, 0x30, 0x67, 0x47, 0x65, 0x75, 0x76, 0x6E}:
            print(rec)


if __name__ == "__main__":
    main()
