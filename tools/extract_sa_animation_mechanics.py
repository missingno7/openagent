from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_asm(ep: int):
    path = ROOT / "dissassembly" / f"SAM{ep}_unpacked_linear_8086.asm"
    out = []
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(.*)", line)
        if m:
            out.append((int(m.group(1), 16), m.group(3).strip(), line.rstrip()))
    return out


def context(items, idx, before=8, after=6):
    return [line for _a, _t, line in items[max(0, idx-before): min(len(items), idx+after+1)]]


def extract(ep: int):
    items = parse_asm(ep)
    player_state_writes = []
    actor_frame_writes = []
    actor_sprite_writes = []
    actor_dir_writes = []
    jump_anim_toggle = []

    for idx, (addr, text, line) in enumerate(items):
        m = re.match(r"movw\s+\$0x([0-9a-f]+),0x3500$", text)
        if m:
            player_state_writes.append({
                "addr": f"0x{addr:05X}",
                "state": int(m.group(1), 16),
                "context": context(items, idx),
            })
        if "0x34d6" in text:
            actor_frame_writes.append({"addr": f"0x{addr:05X}", "text": text, "context": context(items, idx, 5, 5)})
        if "0x34e0" in text:
            actor_sprite_writes.append({"addr": f"0x{addr:05X}", "text": text, "context": context(items, idx, 5, 5)})
        if "0x34e2" in text:
            actor_dir_writes.append({"addr": f"0x{addr:05X}", "text": text, "context": context(items, idx, 5, 5)})
        if addr in (0x1a77, 0x1a7e, 0x1a86):
            jump_anim_toggle.append({"addr": f"0x{addr:05X}", "text": text, "context": context(items, idx, 6, 6)})

    # Hand-labelled summary from the above writes.  Keep this in the generated
    # file so the facts can be regenerated/rechecked against SAM1/SAM2/SAM3.
    summary = {
        "player_state_addr": "DS:3500",
        "player_state_interpretation": {
            "0x01": "right-facing/right-walk base frame; also restored when releasing left while right remains held",
            "0x05": "left-facing/left-walk base frame; also restored when releasing right while left remains held",
            "0x09": "right-facing idle/standing after right release or some scripted placement paths",
            "0x0A": "left-facing idle/standing after left release or no horizontal key",
            "0x0B": "right-facing alternate/collision state used together with 0x01/0x09/0x0D checks",
            "0x0D": "right-facing firing/armed overlay state when DS:6EC1 is set",
            "0x0E": "left-facing firing/armed overlay state when DS:6EC1 is set",
            "0x0F": "jump/upward animation frame A",
            "0x10": "jump/upward animation frame B",
        },
        "player_jump_animation": "When DS:69F5 is non-zero, SAM1 0x1A77..0x1A8C toggles DS:3500 between 0x0F and 0x10 every jump tick before applying the table-driven Y displacement.",
        "actor_frame_counter": "DS:34D6 + slot*0x20 is an animation frame/counter. Horizontal walkers use 0x01..0x13 for one direction and 0x15..0x27 for the other; collision/state code resets or wraps the counter.",
        "actor_sprite_id": "DS:34E0 + slot*0x20 stores the current sprite/object id selected by actor state code. Examples seen in SAM1 include 0x00A7 and 0x0271.",
        "actor_direction": "DS:34E2 + slot*0x20 stores horizontal direction (+1 or -1). Collision code negates it when side probes hit runtime +0x1CC body collision.",
    }
    return {
        "episode": ep,
        "summary": summary,
        "player_state_writes": player_state_writes,
        "actor_frame_counter_refs": actor_frame_writes,
        "actor_sprite_refs": actor_sprite_writes,
        "actor_direction_refs": actor_dir_writes,
        "jump_animation_toggle_refs": jump_anim_toggle,
    }


def main():
    out_dir = ROOT / "docs" / "derived_mechanics"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {f"SAM{ep}": extract(ep) for ep in (1, 2, 3)}
    (out_dir / "animation_mechanics.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"wrote {out_dir / 'animation_mechanics.json'}")
    for ep in (1, 2, 3):
        d = data[f"SAM{ep}"]
        print(f"SAM{ep}: {len(d['player_state_writes'])} player state writes, {len(d['actor_frame_counter_refs'])} actor frame refs")


if __name__ == "__main__":
    main()
