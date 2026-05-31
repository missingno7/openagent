"""Prototype overworld/island-map logic.

Level 0 is a top-down island map, not a side-view mission.  This module keeps
all current overworld assumptions in one place so they can be audited against
ASM without mixing them with mission platformer code.

Accuracy status after pass 102:
- data_verified: level 0 layout, raw player marker 0x59, 0x4D/0x4E wide
  building footprint, and 16 row-major entrance anchors per episode.
- asm_partial: top-down movement/collision follows SAM1:0xBAF5..0xBC0A
  and SAM1:0xB7D9..0xB8B0, including camera-register scrolling and
  exact 10x16 origin-rect probes.
- asm_partial: level-0 player draw now uses the same DS:3500/34F6 animation
  family as the EXE draw path instead of a fixed sprite/offset.
- asm_partial: entrance trigger/release is automatic and player-origin based;
  completion redraw uses the EXE-adjacent bank-1 checked-house tile family,
  and completed houses remain re-enterable after leaving and walking back in.
- heuristic: exact entrance-to-level mapping, persistent flags, and popup/table windows still need
  dedicated traces.
"""

from __future__ import annotations

from PIL import Image

from .animation import (
    PLAYER_STATE_IDLE_LEFT,
    PLAYER_STATE_IDLE_RIGHT,
    PLAYER_STATE_WALK_LEFT,
    PLAYER_STATE_WALK_RIGHT,
    PLAYER_WALK_COUNTER_MAX,
    PLAYER_WALK_COUNTER_START,
    PLAYER_WALK_COUNTER_STEP,
)
from .collision import PLAYER_COLLISION_BOTTOM, PLAYER_COLLISION_LEFT, PLAYER_COLLISION_RIGHT
from .game_constants import DOS_TICK_HZ, PLAYER_H, PLAYER_W
from .level_model import iter_map_cells
from .player_motion import horizontal_step_for_hold_ticks
from .semantics import WORLD_ENTRANCE_CODES, WORLD_PLAYER_CODE

from openagent.game_assets.constants import LEVEL_H, LEVEL_W, TILE


WORLD_CAMERA_MAX_X = 0x140
WORLD_CAMERA_MAX_Y = 0x00B8
WORLD_CAMERA_RIGHT_MARGIN = 0x00AA
WORLD_CAMERA_LEFT_MARGIN = 0x0096
WORLD_CAMERA_VERTICAL_MARGIN = 0x0050
WORLD_CAMERA_CENTER_X = 0x00A0
WORLD_CAMERA_CENTER_Y = 0x0064


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
                return float(cell.x * TILE), float(cell.y * TILE)
        return 32.0, 32.0

    def world_entrances(self) -> list[tuple[int, int, int]]:
        """Return row-major entrance anchors as prototype level links.

        World-map buildings are context-specific raw tokens.  ``0x4D`` and
        ``0x4E`` are the two halves of the wide building; count the left
        ``0x4D`` half as the entrance anchor and include ``0x4E`` only when it
        appears without that left-half neighbour.  ``0x4F`` and ``0x50`` are
        single-cell building markers.  The exact EXE table that maps anchors to
        mission numbers is still open, so level numbers remain row-major.
        """
        info = self.episode.levels[0]
        entrances: list[tuple[int, int, int]] = []
        cells = {(cell.x, cell.y, cell.layer): cell for cell in iter_map_cells(info)}
        for cell in iter_map_cells(info):
            if cell.code not in WORLD_ENTRANCE_CODES:
                continue
            if cell.code == 0x4E and cells.get((cell.x - 1, cell.y, cell.layer)) and cells[(cell.x - 1, cell.y, cell.layer)].code == 0x4D:
                continue
            entrances.append((cell.x, cell.y, len(entrances) + 1))
        return entrances

    def world_entrance_source_cells(self, level: int) -> tuple:
        """Return source cells that form a row-major world-map entrance.

        The raw ``0x4D`` building has a paired ``0x4E`` tile immediately to the
        right.  Completion redraw and auto-enter overlap must treat the two raw
        cells as one building footprint.
        """
        info = self.episode.levels[0]
        entrances = self.world_entrances()
        if level < 1 or level > len(entrances):
            return ()
        x, y, _ = entrances[level - 1]
        by_pos_layer = {(cell.x, cell.y, cell.layer): cell for cell in iter_map_cells(info)}
        anchor = by_pos_layer.get((x, y, "bg")) or next((cell for cell in iter_map_cells(info) if cell.x == x and cell.y == y and cell.code in WORLD_ENTRANCE_CODES), None)
        if anchor is None:
            return ()
        cells = [anchor]
        if anchor.code == 0x4D:
            right = by_pos_layer.get((anchor.x + 1, anchor.y, anchor.layer))
            if right is not None and right.code == 0x4E:
                cells.append(right)
        return tuple(cells)

    def completed_world_levels(self) -> set[int]:
        if not hasattr(self, "completed_world_levels_by_episode"):
            self.completed_world_levels_by_episode = {}
        return self.completed_world_levels_by_episode.setdefault(self.episode_number, set())

    def world_level_completed(self, level: int) -> bool:
        return level in self.completed_world_levels()

    def completed_world_entrance_source_keys(self) -> set[tuple[int, int, int, str]]:
        keys: set[tuple[int, int, int, str]] = set()
        for level in self.completed_world_levels():
            for cell in self.world_entrance_source_cells(level):
                keys.add((cell.x, cell.y, cell.code, cell.layer))
        return keys

    def draw_completed_world_entrance_overlays(self) -> None:
        """Draw checked/completed house cels over the baked world map.

        The level-0 token parser has active cA visuals ``0x0201..0x0204`` and
        the neighbouring checked family ``0x0205..0x0208``.  In the decoded
        bank-1 atlas those are active tiles 12..15 and checked tiles 16..19.
        """
        if self.level_image is None:
            return
        for level in self.completed_world_levels():
            for cell in self.world_entrance_source_cells(level):
                tile_no = 16 + (cell.code - 0x4D)
                tile = self.episode.tiles16.get(1, tile_no)
                if tile is not None:
                    self.level_image.alpha_composite(tile, (cell.x * TILE, cell.y * TILE))

    def world_cell_blocked(self, x: int, y: int) -> bool:
        """Return the ASM body-collision byte used by level-0 movement.

        Pass 98 traced the top-down movement routine at ``SAM1:0xBAF5`` and
        its collision helper at ``SAM1:0xB7D9``.  The helper does not classify
        raw island-map bytes visually.  It samples the already-built runtime
        collision cell byte ``+0x1CC`` at the player rectangle corners.  This
        wrapper exposes that byte for debug/status helpers.
        """
        if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
            return True
        cell = self.runtime_collision_cell(x, y)
        return bool(cell and cell.body_solid)

    def world_player_clear_at(self, x: float, y: float) -> bool:
        """Mirror the ``SAM1:0xB7D9`` top-down body test.

        The helper is not a generic sprite-boundary clamp.  It receives a
        proposed ``dx/dy`` from the caller, adds it to ``DS:34EE/34F0``, and
        probes only the 10x16 gameplay rectangle: X ``+3/+12`` and
        Y ``+0/+15``.  The four probes read runtime byte ``+0x1CC``; byte
        ``+0x1CD`` is ignored for level-0 navigation.
        """
        probes = (
            (x + PLAYER_COLLISION_LEFT, y),
            (x + PLAYER_COLLISION_RIGHT, y),
            (x + PLAYER_COLLISION_LEFT, y + PLAYER_COLLISION_BOTTOM),
            (x + PLAYER_COLLISION_RIGHT, y + PLAYER_COLLISION_BOTTOM),
        )
        for px, py in probes:
            tx = int(px) // TILE
            ty = int(py) // TILE
            if self.world_cell_blocked(tx, ty):
                return False
        return True

    def world_player_clear_offset(self, dx: float, dy: float) -> bool:
        """ASM call shape for ``SAM1:0xB7D9``.

        The EXE passes the attempted displacement to the helper and only writes
        the new position after the helper returns true.  Keeping this wrapper
        makes it harder to accidentally reintroduce pre-clamped destination
        coordinates.
        """
        p = self.player
        return self.world_player_clear_at(p.x + dx, p.y + dy)

    def world_player_blocked(self) -> bool:
        p = self.player
        return not self.world_player_clear_at(p.x, p.y)

    def init_world_camera_from_player(self) -> None:
        """Initialize the reconstructed ``DS:6838/683A`` scroll registers.

        Teleport arrival code at ``SAM1:0x2059..0x209F`` recenters as
        ``x - 0xA0`` / ``y - 0x64`` and clamps to ``0..0x140`` / ``0..0xB8``.
        Use the same rule when entering or resetting level 0.
        """
        p = self.player
        self.world_camera_x = self.clamp_world_camera_x(int(p.x) - WORLD_CAMERA_CENTER_X)
        self.world_camera_y = self.clamp_world_camera_y(int(p.y) - WORLD_CAMERA_CENTER_Y)

    @staticmethod
    def clamp_world_camera_x(value: int) -> int:
        return max(0, min(WORLD_CAMERA_MAX_X, int(value)))

    @staticmethod
    def clamp_world_camera_y(value: int) -> int:
        return max(0, min(WORLD_CAMERA_MAX_Y, int(value)))

    def move_world_right(self, step: int) -> None:
        if self.collision_enabled and not self.world_player_clear_offset(step, 0):
            return
        p = self.player
        if self.world_camera_x < WORLD_CAMERA_MAX_X and self.world_camera_x + WORLD_CAMERA_RIGHT_MARGIN < p.x:
            self.world_camera_x = self.clamp_world_camera_x(self.world_camera_x + step)
        p.x += step

    def move_world_left(self, step: int) -> None:
        if self.collision_enabled and not self.world_player_clear_offset(-step, 0):
            return
        p = self.player
        if self.world_camera_x > 0 and self.world_camera_x + WORLD_CAMERA_LEFT_MARGIN > p.x:
            self.world_camera_x = self.clamp_world_camera_x(self.world_camera_x - step)
        p.x -= step

    def move_world_down(self) -> None:
        if self.collision_enabled and not self.world_player_clear_offset(0, 4):
            return
        p = self.player
        if self.world_camera_y < WORLD_CAMERA_MAX_Y and self.world_camera_y + WORLD_CAMERA_VERTICAL_MARGIN < p.y:
            self.world_camera_y = self.clamp_world_camera_y(self.world_camera_y + 4)
        p.y += 4

    def move_world_up(self) -> None:
        if self.collision_enabled and not self.world_player_clear_offset(0, -4):
            return
        p = self.player
        if self.world_camera_y > 0 and self.world_camera_y + WORLD_CAMERA_VERTICAL_MARGIN > p.y:
            self.world_camera_y = self.clamp_world_camera_y(self.world_camera_y - 4)
        p.y -= 4

    def move_world_axis(self, dx: float, dy: float) -> None:
        """Compatibility wrapper for older tools/tests.

        Runtime input now uses the dedicated ``move_world_*`` methods above so
        camera updates follow ``SAM1:0xBAF5`` exactly.  This wrapper keeps
        external probes simple while preserving the important no-pre-clamp
        collision behaviour.
        """
        if dx == 0 and dy == 0:
            return
        if not self.collision_enabled or self.world_player_clear_offset(dx, dy):
            self.player.x += dx
            self.player.y += dy

    def world_horizontal_step(self) -> int:
        self.player.move_hold_ticks += 1
        return horizontal_step_for_hold_ticks(self.player.move_hold_ticks, self.player.speed_bonus_step)

    def update_world_player(self, dt: float) -> None:
        self._logic_accum = min(self._logic_accum + dt, (1.0 / DOS_TICK_HZ) * 5.0)
        while self._logic_accum >= 1.0 / DOS_TICK_HZ:
            self._logic_accum -= 1.0 / DOS_TICK_HZ
            self.snapshot_player_render_position()
            self._prev_world_camera = (float(self.world_camera_x), float(self.world_camera_y))
            self.update_world_player_tick()

    def update_world_player_animation_state(self, *, left: bool, right: bool, up: bool, down: bool) -> None:
        """Mirror the level-0 DS:3500 direction/animation state policy.

        The keyboard branch around ``SAM1:0x60..0x460`` turns horizontal input
        into walk-right/walk-left states and uses the current facing direction
        when only vertical flags are active.  It does not have separate
        up/down sprites for the island map.
        """
        p = self.player
        moving = left or right or up or down
        if right:
            p.facing = 1
            p.anim_state = PLAYER_STATE_WALK_RIGHT
        elif left:
            p.facing = -1
            p.anim_state = PLAYER_STATE_WALK_LEFT
        elif moving:
            p.anim_state = PLAYER_STATE_WALK_RIGHT if p.facing >= 0 else PLAYER_STATE_WALK_LEFT
        else:
            p.anim_state = PLAYER_STATE_IDLE_RIGHT if p.facing >= 0 else PLAYER_STATE_IDLE_LEFT
            p.walk_counter = PLAYER_WALK_COUNTER_START
            return

        if p.anim_state in (PLAYER_STATE_WALK_RIGHT, PLAYER_STATE_WALK_LEFT):
            p.walk_counter += PLAYER_WALK_COUNTER_STEP
            if p.walk_counter > PLAYER_WALK_COUNTER_MAX:
                p.walk_counter = PLAYER_WALK_COUNTER_START

    def update_world_player_tick(self) -> None:
        p = self.player
        if self.update_teleport_tick():
            p.move_hold_ticks = 0
            self.last_world_position = (p.x, p.y)
            return

        left = any(k in self.keys for k in ("Left", "a", "A"))
        right = any(k in self.keys for k in ("Right", "d", "D"))
        up = any(k in self.keys for k in ("Up", "w", "W"))
        down = any(k in self.keys for k in ("Down", "s", "S"))

        self.update_world_player_animation_state(left=left, right=right, up=up, down=down)

        # ``SAM1:0xBAF5`` processes flags in this fixed order: right, left,
        # down, up.  The keyboard ISR makes opposing directions mutually
        # exclusive, so normally only one horizontal and one vertical flag can
        # be set, but preserving the order keeps diagonal corner behaviour and
        # camera scrolling close to the EXE.
        moved_horizontally = False
        if right:
            self.move_world_right(self.world_horizontal_step())
            moved_horizontally = True
        if left:
            self.move_world_left(self.world_horizontal_step())
            moved_horizontally = True
        if not moved_horizontally and not (up or down):
            # Keyboard ISR clears DS:681E only once all direction flags are off.
            p.move_hold_ticks = 0

        if down:
            self.move_world_down()
        if up:
            self.move_world_up()

        if self.check_world_entrance_touch():
            return
        self.check_teleporter_touch()
        self.last_world_position = (p.x, p.y)

    def world_player_overlaps_cells(self, cells: tuple) -> bool:
        p = self.player
        left = p.x + PLAYER_COLLISION_LEFT
        right = p.x + PLAYER_COLLISION_RIGHT
        top = p.y
        bottom = p.y + PLAYER_COLLISION_BOTTOM
        for cell in cells:
            cell_left = cell.x * TILE
            cell_right = cell_left + TILE - 1
            cell_top = cell.y * TILE
            cell_bottom = cell_top + TILE - 1
            if not (right < cell_left or left > cell_right or bottom < cell_top or top > cell_bottom):
                return True
        return False


    def world_player_origin_inside_cells(self, cells: tuple) -> bool:
        """Return true only while DS:34EE/34F0 is inside an entrance cell.

        The release gate after returning from a mission should suppress the
        immediate re-entry caused by spawning on the same building, but it
        must not permanently disable completed houses.  Using the full 10x16
        body overlap here kept the gate armed while only an edge of the player
        still touched the tile; the ASM movement/entry flow is better modeled
        by clearing the gate once the player origin has actually left the
        building footprint.
        """
        p = self.player
        ox = int(p.x)
        oy = int(p.y)
        for cell in cells:
            if cell.x * TILE <= ox <= cell.x * TILE + TILE - 1 and cell.y * TILE <= oy <= cell.y * TILE + TILE - 1:
                return True
        return False

    def world_entrance_level_at_player(self) -> int | None:
        release_level = getattr(self, "world_entry_release_level", None)
        release_still_inside = False
        for _x, _y, level in self.world_entrances():
            cells = self.world_entrance_source_cells(level)
            # Entrance dispatch is origin based, not broad 10x16 body-overlap
            # based.  This keeps checked/completed houses re-enterable once the
            # player actually walks back into their footprint, while avoiding
            # accidental re-entry from a lingering body edge while leaving.
            inside = self.world_player_origin_inside_cells(cells)
            if level == release_level:
                release_still_inside = inside
                if release_still_inside:
                    continue
                self.world_entry_release_level = None
            if inside:
                return level
        if release_level is not None and not release_still_inside:
            self.world_entry_release_level = None
        return None

    def enter_world_level(self, level: int) -> None:
        p = self.player
        self.last_world_position = (p.x, p.y)
        self.world_entry_release_level = level
        self.level_index = level
        # I have not found a dedicated mission-entry SFX at the world-map
        # dispatcher yet; do not guess one here.  Startup/title call-site
        # SAM1:0x1B440 uses sound 0x15, but that is broader than per-level
        # entry and is documented in pass52.
        self.load_level(reset_player=True)

    def check_world_entrance_touch(self) -> bool:
        level = self.world_entrance_level_at_player()
        if level is None:
            return False
        self.enter_world_level(level)
        return True

    def try_enter_world_level(self) -> None:
        # Kept for keyboard/backwards compatibility.  The original island map
        # enters a building as soon as the player walks into its marker.
        level = self.world_entrance_level_at_player()
        if level is not None:
            self.enter_world_level(level)

    def draw_world_entrance_numbers(self, frame: Image.Image, cam_x: int, cam_y: int) -> None:
        # Playtest overlay only.  It deliberately uses the original 8x8 UI
        # renderer but is not claimed to match the game's popup/table behavior.
        for x, y, level in self.world_entrances():
            sx = x * TILE - cam_x
            sy = y * TILE - cam_y
            view_w, view_h = self.viewport_size()
            if -16 <= sx < view_w and -16 <= sy < view_h:
                self.draw_hud_digit_string(frame, sx, sy, str(level), bank=2)
