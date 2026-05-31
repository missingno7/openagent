from __future__ import annotations

from .collision import PLAYER_COLLISION_BOTTOM
from .game_constants import PLAYER_H, PLAYER_VERTICAL_COUNTER_INITIAL, PLAYER_W
from .level_model import iter_map_cells
from .semantics import TELEPORTER_CODE
from .sound import SOUND_TELEPORT

from openagent.game_assets.constants import LEVEL_H, LEVEL_W, TILE


class TeleportMixin:
    """Mission and world-map teleporter behaviour.

    The timing/state here reconstructs the DS:69E0/69E2 teleporter countdown
    separately from player movement so ``runtime.py`` can keep the main
    fixed-step order readable.
    """

    def reset_teleport_state(self) -> None:
        self.teleport_active = False
        self.teleport_timer_ticks = 0
        self.teleport_target = None
        self.teleport_warped = False

    def teleporter_cells(self):
        if self._teleporter_cells_cache is None:
            info = self.episode.levels[self.level_index]
            self._teleporter_cells_cache = [cell for cell in iter_map_cells(info) if cell.code == TELEPORTER_CODE]
            self._teleporter_cells_cache.sort(key=lambda cell: (cell.y, cell.x, cell.layer))
        return self._teleporter_cells_cache

    def mission_player_body_clear_at(self, x: float, y: float) -> bool:
        old_x, old_y = self.player.x, self.player.y
        self.player.x, self.player.y = x, y
        try:
            return not self.player_collides()
        finally:
            self.player.x, self.player.y = old_x, old_y

    def world_player_body_clear_at(self, x: float, y: float) -> bool:
        old_x, old_y = self.player.x, self.player.y
        self.player.x, self.player.y = x, y
        try:
            return not self.world_player_blocked()
        finally:
            self.player.x, self.player.y = old_x, old_y

    def player_centered_on_world_teleporter(self, cell) -> bool:
        # Keep the older, looser overworld behaviour.  The pass-88 ASM audit is
        # for mission runtime visual 0x00B7; level-0 navigation still uses the
        # prototype island-map movement rules.
        p = self.player
        center_x = p.x + PLAYER_W / 2
        center_y = p.y + PLAYER_H / 2
        pad_cx = cell.x * TILE + TILE / 2
        pad_cy = cell.y * TILE + TILE / 2
        return abs(center_x - pad_cx) <= 8 and abs(center_y - pad_cy) <= 12

    def player_overlaps_teleporter_pad(self, cell) -> bool:
        # Approximate the cA=0x00B7 pad contact used by the interaction
        # dispatcher.  This is intentionally still a real pad overlap test,
        # used for arming the teleporter before the ASM-style +/-2 X alignment
        # gate below.
        p = self.player
        left = p.x + 3
        right = p.x + 12
        top = p.y
        bottom = p.y + PLAYER_COLLISION_BOTTOM
        pad_left = cell.x * TILE
        pad_right = pad_left + TILE - 1
        pad_top = cell.y * TILE
        pad_bottom = pad_top + TILE - 1
        return not (right < pad_left or left > pad_right or bottom < pad_top or top > pad_bottom)

    def player_still_in_teleporter_x_footprint(self, cell) -> bool:
        # There is no input-direction test in the teleporter branch.  The EXE
        # avoids immediate ping-pong mostly through DS:69E0/69E2 and the +/-3
        # destination X nudge.  The reconstructed broad interaction pass can
        # otherwise clear the release gate too early when Y is slightly outside
        # the pad cell, then the first opposite-direction step can cross back
        # through the +/-2 X alignment band.  Keep the destination armed until
        # the player's actual 0xB7D9 collision footprint has left the pad column.
        p = self.player
        left = p.x + 3
        right = p.x + 12
        pad_left = cell.x * TILE
        pad_right = pad_left + TILE - 1
        return not (right < pad_left or left > pad_right)

    def player_aligned_on_teleporter(self, cell) -> bool:
        # SAM1:0xD493..0xD4CB masks the pad X to a 16px boundary, then compares
        # DS:34EE (player X) to that boundary with a strict +/-2 px tolerance.
        # The previous center-based +/-8 test was too broad: after the ASM's
        # destination nudge (x +/- 3) it could immediately re-arm the return pad.
        if not self.player_overlaps_teleporter_pad(cell):
            return False
        return abs(self.player.x - cell.x * TILE) <= 2

    def update_teleport_release_gate(self) -> None:
        # While DS:69E0 is active the EXE refuses to arm another teleport.  On
        # arrival the stored destination X is deliberately nudged by +/-3 px, so
        # the next dispatcher pass is not aligned.  Keep an explicit
        # reconstruction gate until the player's B7D9 X footprint leaves the
        # destination pad column; otherwise a Y-misaligned broad overlap can
        # clear the gate before the player has actually walked out.
        if self.teleport_release_cell is None:
            return
        for cell in self.teleporter_cells():
            if (cell.x, cell.y, cell.layer) == self.teleport_release_cell:
                if self.player_still_in_teleporter_x_footprint(cell):
                    return
                break
        self.teleport_release_cell = None

    def find_partner_teleporter(self, source_cell):
        for cell in self.teleporter_cells():
            if (cell.x, cell.y, cell.layer) != (source_cell.x, source_cell.y, source_cell.layer):
                return cell
        return None

    def choose_teleport_target_position(self, target_cell) -> tuple[float, float]:
        # SAM1:0xD534..0xD549 stores ((target_col - 1) << 4,
        # (target_row - 1) << 4).  It then probes runtime byte +0x1CC one tile
        # below that target row: if that body-solid byte is non-zero it nudges
        # X by +3, otherwise by -3.  Do not search for an arbitrary clear
        # fallback; the +/-3 offset is part of why the destination pad does not
        # instantly satisfy the later +/-2 alignment test.
        base_x = float(target_cell.x * TILE)
        base_y = float(target_cell.y * TILE)
        if self.is_world_map:
            candidates = [(base_x - 3, base_y), (base_x + 3, base_y), (base_x, base_y)]
            for x, y in candidates:
                if 0 <= x <= LEVEL_W * TILE - PLAYER_W and 0 <= y <= LEVEL_H * TILE - PLAYER_H and self.world_player_body_clear_at(x, y):
                    return x, y
            return base_x, base_y
        probe = self.runtime_collision_cell(target_cell.x, target_cell.y + 1)
        nudge = 3 if bool(probe and probe.body_solid) else -3
        target_x = min(max(base_x + nudge, 0.0), float(LEVEL_W * TILE - PLAYER_W))
        target_y = min(max(base_y, 0.0), float(LEVEL_H * TILE - PLAYER_H))
        return target_x, target_y

    def start_teleport(self, source_cell, target_cell) -> None:
        self.teleport_active = True
        self.teleport_timer_ticks = 0x13
        self.teleport_target = self.choose_teleport_target_position(target_cell)
        self.teleport_release_cell = (target_cell.x, target_cell.y, target_cell.layer)
        self.teleport_warped = False
        self.player.vx = 0.0
        self.player.vy = 0.0
        self.player.move_hold_ticks = 0
        self.player.walk_time = 0.0
        self.play_sound(SOUND_TELEPORT)

    def check_teleporter_touch(self) -> None:
        self.update_teleport_release_gate()
        if self.teleport_active or self.teleport_release_cell is not None:
            return
        for cell in self.teleporter_cells():
            on_pad = self.player_centered_on_world_teleporter(cell) if self.is_world_map else self.player_aligned_on_teleporter(cell)
            if not on_pad:
                continue
            target = self.find_partner_teleporter(cell)
            if target is None:
                return
            self.start_teleport(cell, target)
            return

    def update_teleport_tick(self) -> bool:
        if not self.teleport_active:
            return False
        self.teleport_timer_ticks -= 1
        if not self.teleport_warped and self.teleport_timer_ticks <= 0 and self.teleport_target is not None:
            self.player.x, self.player.y = self.teleport_target
            self.player.vx = 0.0
            self.player.vy = 0.0
            self.player.grounded = False
            self.player.jump_anim_timer = 0
            self.player.fall_ticks = PLAYER_VERTICAL_COUNTER_INITIAL
            self.teleport_warped = True
            if self.is_world_map:
                self.init_world_camera_from_player()
                self.last_world_position = (self.player.x, self.player.y)
        if self.teleport_timer_ticks <= -0x13:
            self.reset_teleport_state()
        return True

