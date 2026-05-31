#!/usr/bin/env python3
"""Audit level-0/overworld raw data without claiming ASM accuracy.

This script is intentionally data-only.  It helps keep the current level-0
facts reproducible while the ASM movement/collision/entrance routines are still
being traced.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from openagent.loader import load_campaign  # noqa: E402
from openagent.level_model import iter_map_cells  # noqa: E402
from openagent.semantics import WORLD_ENTRANCE_CODES, WORLD_PLAYER_CODE  # noqa: E402

IGNORED_EMPTY = {0x00, 0x20, ord('*')}


def analyse_episode(campaign, ep: int) -> dict:
    episode = campaign.bundle.episodes[ep]
    level0 = episode.levels[0]
    counts: Counter[int] = Counter()
    positions: dict[int, list[dict[str, int | str]]] = defaultdict(list)
    for cell in iter_map_cells(level0):
        if cell.code in IGNORED_EMPTY:
            continue
        counts[cell.code] += 1
        positions[cell.code].append({"x": cell.x, "y": cell.y, "layer": cell.layer, "raw_row": cell.raw_row})

    # Runtime/pass101 treats adjacent 0x4D/0x4E as a single wide building
    # footprint.  Keep this audit aligned with the playable entrance anchors
    # while still reporting the raw code at the anchor cell.
    entrances = []
    by_pos_layer = {(int(p["x"]), int(p["y"]), str(p["layer"])): code
                    for code, plist in positions.items() for p in plist}
    for code in sorted(WORLD_ENTRANCE_CODES):
        for p in positions.get(code, []):
            if code == 0x4E and by_pos_layer.get((int(p["x"]) - 1, int(p["y"]), str(p["layer"]))) == 0x4D:
                continue
            entrances.append({"code": f"0x{code:02X}", **p})
    entrances.sort(key=lambda p: (int(p["y"]), int(p["x"]), str(p["layer"])))
    for i, ent in enumerate(entrances, start=1):
        ent["prototype_row_major_level"] = i

    player_markers = [{"code": f"0x{WORLD_PLAYER_CODE:02X}", **p} for p in positions.get(WORLD_PLAYER_CODE, [])]
    top_codes = [{"code": f"0x{code:02X}", "count": count} for code, count in counts.most_common(40)]
    unique_codes = [f"0x{code:02X}" for code in sorted(counts)]
    return {
        "episode": ep,
        "player_markers": player_markers,
        "entrances": entrances,
        "entrance_count": len(entrances),
        "top_codes": top_codes,
        "unique_codes": unique_codes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default=str(ROOT / "game_data"), help="Directory containing SAM?.* files")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a compact text report")
    args = parser.parse_args()

    campaign = load_campaign(Path(args.source))
    try:
        report = [analyse_episode(campaign, ep) for ep in campaign.episode_numbers]
    finally:
        campaign.cleanup()

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    for ep in report:
        print(f"Episode {ep['episode']}: level 0 / overworld")
        markers = ", ".join(f"({m['x']},{m['y']})/{m['layer']}" for m in ep["player_markers"])
        print(f"  player marker 0x{WORLD_PLAYER_CODE:02X}: {markers or 'none'}")
        print(f"  entrances: {ep['entrance_count']}")
        for ent in ep["entrances"]:
            print(
                f"    #{ent['prototype_row_major_level']:02d} {ent['code']} "
                f"at ({ent['x']},{ent['y']})/{ent['layer']} raw_row={ent['raw_row']}"
            )
        print("  top raw codes: " + ", ".join(f"{c['code']}×{c['count']}" for c in ep["top_codes"][:12]))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
