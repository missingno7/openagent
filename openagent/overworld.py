"""Prototype overworld/island-map logic.

Level 0 is a top-down island map, not a side-view mission.  This module keeps
all current overworld assumptions in one place so they can be audited against
ASM without mixing them with mission platformer code.

Accuracy status, pass 77:
- data_verified: level 0 layout, raw player marker 0x59, and entrance marker
  count/order (0x4D/0x4F/0x50 gives 16 entrances per episode).
- heuristic: collision classes and exact input/entry popup behavior.  The EXE
  overworld collision dispatcher still needs a dedicated trace.
"""

from __future__ import annotations

from PIL import Image

from .game_constants import PLAYER_H, PLAYER_W
from .level_model import codes_at, iter_map_cells
from .semantics import WORLD_BLOCKED_CODES, WORLD_ENTRANCE_CODES, WORLD_PLAYER_CODE

from openagent.game_assets.constants import LEVEL_H, LEVEL_W, TILE


class OverworldMixin:
    """Level-0 island-map helpers.

    The runtime class supplies ``episode``, ``level_index``, ``player``,
    ``collision_enabled``, ``load_level()``, ``draw_hud_digit_string()`` and
    ``viewport_size()``.  Keeping this as a mixin avoids a large refactor while
    making the remaining heuristics visible and easy to replace once the ASM
    pass is complete.
    """

    def find_world_spawn(self) -> tuple[float, float]:
        info = self.episode.levels[0]
        for cell in iter_map_cells(info):
            if cell.code == WORLD_PLAYER_CODE:
                return float(cell.x * TILE + 2), float(cell.y * TILE + 1)
        return 32.0, 32.0

    def world_entrances(self) -> list[tuple[int, int, int]]:
        """Return row-major entrance candidates as prototype level links.

        Data fact: each episode has exactly sixteen raw markers in level 0 when
        counting 0x4D, 0x4F and 0x50.  The original EXE mapping from marker to
        mission number is still open, so this remains a named prototype rather
        than a claimed ASM-verified rule.
        """
        entrances: list[tuple[int, int, int]] = []
        for cell in iter_map_cells(self.episode.levels[0]):
            if cell.code in WORLD_ENTRANCE_CODES:
                entrances.append((cell.x, cell.y, len(entrances) + 1))
        return entrances

    def world_cell_blocked(self, x: int, y: int) -> bool:
        """Heuristic island-map collision predicate.

        Mission collision replays the EXE runtime-cell table.  Level 0 must not
        use that table because identical raw bytes have different meanings on
        the island map.  This classification is deliberately isolated here and
        marked heuristic until the overworld ASM dispatcher is traced.
        """
        if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
            return True
        info = self.episode.levels[0]
        return any(code in WORLD_BLOCKED_CODES for code in codes_at(info, x, y))

    def world_player_blocked(self) -> bool:
        p = self.player
        probes = [
            (p.x + 2, p.y + 2),
            (p.x + PLAYER_W - 3, p.y + 2),
            (p.x + 2, p.y + PLAYER_H - 3),
            (p.x + PLAYER_W - 3, p.y + PLAYER_H - 3),
        ]
        return any(self.world_cell_blocked(int(x) // TILE, int(y) // TILE) for x, y in probes)

    def move_world_axis(self, dx: float, dy: float) -> None:
        p = self.player
        p.x += dx
        p.y += dy
        p.x = min(max(p.x, 0), LEVEL_W * TILE - PLAYER_W)
        p.y = min(max(p.y, 0), LEVEL_H * TILE - PLAYER_H)
        if not self.collision_enabled:
            return

        if self.world_player_blocked():
            step_x = -1 if dx > 0 else 1 if dx < 0 else 0
            step_y = -1 if dy > 0 else 1 if dy < 0 else 0
            while self.world_player_blocked():
                p.x += step_x
                p.y += step_y

    def try_enter_world_level(self) -> None:
        p = self.player
        center_x = p.x + PLAYER_W / 2
        center_y = p.y + PLAYER_H / 2
        best: tuple[float, int] | None = None
        for x, y, level in self.world_entrances():
            dist = abs(center_x - (x * TILE + TILE / 2)) + abs(center_y - (y * TILE + TILE / 2))
            if dist <= 20 and (best is None or dist < best[0]):
                best = (dist, level)
        if best is not None:
            self.last_world_position = (p.x, p.y)
            self.level_index = best[1]
            # I have not found a dedicated mission-entry SFX at the world-map
            # dispatcher yet; do not guess one here.  Startup/title call-site
            # SAM1:0x1B440 uses sound 0x15, but that is broader than
            # per-level entry and is documented in pass52.
            self.load_level(reset_player=True)

    def draw_world_entrance_numbers(self, frame: Image.Image, cam_x: int, cam_y: int) -> None:
        # Playtest overlay only.  It deliberately uses the original 8x8 UI
        # renderer but is not claimed to match the game's popup/table behavior.
        for x, y, level in self.world_entrances():
            sx = x * TILE - cam_x
            sy = y * TILE - cam_y
            view_w, view_h = self.viewport_size()
            if -16 <= sx < view_w and -16 <= sy < view_h:
                self.draw_hud_digit_string(frame, sx, sy, str(level), bank=2)
