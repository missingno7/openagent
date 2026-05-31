#!/usr/bin/env python3
"""Regression smoke test for mission hard-death runtime visual lookup.

Pass 111 moved collision helpers out of runtime.py.  The hard-death tile path
still calls OpenAgentApp.runtime_visual_ids_for_code at runtime, so this check
keeps the exe-runtime-collision import from silently regressing again.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.runtime import OpenAgentApp
from openagent.semantics import HARD_DEATH_RUNTIME_VISUAL_IDS, WATER_CODE, LASER_FIELD_CODE


def main() -> int:
    water_visuals = OpenAgentApp.runtime_visual_ids_for_code(WATER_CODE)
    assert water_visuals & HARD_DEATH_RUNTIME_VISUAL_IDS, "water raw code must map to hard-death runtime visual id"

    laser_visuals = OpenAgentApp.runtime_visual_ids_for_code(LASER_FIELD_CODE)
    assert laser_visuals & HARD_DEATH_RUNTIME_VISUAL_IDS, "laser-field raw code must map to hard-death runtime visual id"

    print("Runtime hard-death visual lookup smoke OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
