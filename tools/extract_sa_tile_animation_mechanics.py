#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Report EXE/data-derived Secret Agent tile animation notes.")
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument("--out", default="docs/derived_mechanics/pass20_tile_animation_correction.json")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    sys.path.insert(0, str(root / "secret_agent_editor"))
    sys.path.insert(0, str(root))

    from secret_agent_editor.mapping import TILE_MAP, BACKGROUND_MAP
    from secret_agent_editor.tile_animations import ANIMATED_TILES
    from openagent.exe_runtime_collision import RUNTIME_CELL_WRITES

    # Find map codes that draw the animated bank/tile refs.
    tile_users = []
    animated_refs = set(ANIMATED_TILES)
    for code, refs in sorted(TILE_MAP.items()):
        for dx, dy, bank, tile in refs:
            if (bank, tile) in animated_refs:
                writes = RUNTIME_CELL_WRITES.get(code, ())
                tile_users.append({
                    "map_code": f"0x{code:02X}",
                    "draw_ref": {"dx": dx, "dy": dy, "bank": bank, "tile": tile},
                    "runtime_writes": [
                        {
                            "dx": w.dx,
                            "dy": w.dy,
                            "c6": f"0x{w.c6:04X}",
                            "c8": f"0x{w.c8:04X}",
                            "cA": f"0x{w.cA:04X}",
                            "body_solid": w.body_solid,
                            "foot_solid": w.foot_solid,
                            "context": w.context,
                        }
                        for w in writes
                    ],
                })

    background_variants = []
    for bg_code, (bank, tile) in sorted(BACKGROUND_MAP.items()):
        background_variants.append({
            "background_code": bg_code,
            "base": {"bank": bank, "tile": tile},
            "static_variant_codes": {
                "0x35": {"bank": bank, "tile": tile + 1},
                "0x36": {"bank": bank, "tile": tile + 2},
                "0x37": {"bank": bank, "tile": tile + 3},
            },
            "note": "Static background/light variants, not animation phases.",
        })

    data = {
        "summary": (
            "Pass20 correction: 0x35/0x36/0x37 are static background-derived variants. "
            "The observed animated tile case is visual id 0x01F3, decoded as bank 4 tile 48; "
            "the EXE draw branch alternates it with the paired bank 4 tile 0 graphic."
        ),
        "exe_evidence": [
            {
                "sam1_offsets": ["0xE6ED", "0xF609", "0xFBBC", "0x101AC"],
                "condition": "cmp ax,0x01F3",
                "behaviour": "if DS:6840 == 0x10 draw from one bitmap offset, otherwise draw from a second bitmap offset",
            },
            {
                "map_code": "0x60",
                "runtime_cell": "cA=0x01F3",
                "atlas_ref": "bank 4 tile 48",
            },
        ],
        "animated_tiles": [
            {
                "normal_ref": {"bank": bank, "tile": tile},
                "frames": [{"bank": b, "tile": t} for b, t in anim.frames],
                "period_ticks": anim.period_ticks,
                "note": anim.note,
            }
            for (bank, tile), anim in sorted(ANIMATED_TILES.items())
        ],
        "map_codes_using_animated_tiles": tile_users,
        "static_background_variants": background_variants,
    }

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
