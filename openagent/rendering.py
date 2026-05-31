from __future__ import annotations

import math
from typing import Hashable

from PIL import Image, ImageDraw, ImageTk

from .animation import (
    PLAYER_DEATH_TILES,
    bank14_guard_tile,
    multi_tile_actor_refs,
    player_tile,
    satellite_tile,
    state17_landmine_tile,
    state1f_actor_refs,
    state23_contact_bomb_tile,
    state27_actor_refs,
    state2b_actor_refs,
    state2c_tile,
    teleporter_pad_tile,
    teleporter_top_tile,
    teleport_warp_tile,
    walker_tile,
)
from .entities import BeamTrap, Enemy
from .exe_actor_mechanics import beam_phase_for_timer, spike_frame_for_timer
from .exe_runtime_collision import runtime_cell_writes_for_code
from .game_constants import DOS_TICK_HZ, PLAYER_H, PLAYER_W
from .hud import STATUS_BAR_H
from .interpolation import PresentationSmoother, lerp_point
from .semantics import (
    DYNAMIC_MISSION_CODES,
    HIDDEN_PLATFORM_CODE,
    TELEPORTER_CODE,
    WATER_CODE,
    WORLD_PLAYER_CODE,
)

from openagent.game_assets.constants import LEVEL_H, LEVEL_W, TILE
from openagent.game_assets.render import SecretAgentRenderer


class RenderingMixin:
    """Render-only helpers for the Tk/PIL presentation path.

    Gameplay and collision stay in the fixed-tick runtime.  This mixin owns the
    presentation snapshot/interpolation state, camera projection and dynamic
    sprite compositing so ``runtime.py`` can remain focused on simulation order.
    """

    def reset_render_interpolation_state(self) -> None:
        self._prev_player_render_pos = (self.player.x, self.player.y)
        self._prev_world_camera = (float(self.world_camera_x), float(self.world_camera_y))
        self._prev_entity_render_pos = {}
        self._last_render_dt = 1.0 / 60.0
        self._presentation_smoother = PresentationSmoother()
        self.snapshot_dynamic_render_positions(force=True)

    def render_interpolation_smooth_enabled(self) -> bool:
        return bool(getattr(self, "visual_interpolation_smoothing", False))

    def snapshot_player_render_position(self) -> None:
        # Capture the state immediately before a fixed DOS tick mutates the
        # player.  This intentionally has no per-Tk-frame guard: catch-up frames
        # may run multiple fixed ticks, and each tick needs its own previous
        # sample so the next draw only interpolates over one DOS tick.
        # Simulation and collision never read this presentation state.
        self._prev_player_render_pos = (self.player.x, self.player.y)

    def snapshot_dynamic_render_positions(self, *, force: bool = False) -> None:
        # This is render-only state: it is never consulted by collision,
        # projectiles, actor logic or interaction checks.  Player snapshots are
        # handled separately by routines that actually mutate the player;
        # otherwise an actor-only tick could collapse an in-progress player lerp
        # to current and cause a tiny visual snap.
        positions: dict[int, tuple[float, float]] = {}
        for collection in (
            self.entities.platforms,
            self.entities.barrels,
            self.entities.satellites,
            self.entities.enemies,
            self.entities.projectiles,
            self.entities.explosions,
            self.entities.score_popups,
        ):
            for obj in collection:
                positions[id(obj)] = (float(obj.x), float(obj.y))
        self._prev_entity_render_pos = positions
        smoother = getattr(self, "_presentation_smoother", None)
        if smoother is not None:
            smoother.forget_prefix("entity", {("entity", key) for key in positions})

    def snapshot_world_camera_render_position(self) -> None:
        # Level-0 camera registers DS:6838/683A are fixed-tick state.  Keep a
        # presentation-only state so smooth mode can apply the same general
        # filter to camera scrolls as it does to actors and the player.
        self._prev_world_camera = (float(self.world_camera_x), float(self.world_camera_y))

    def render_interpolation_alpha(self, accumulator: float) -> float:
        if not self.visual_interpolation_enabled:
            return 1.0
        tick_dt = 1.0 / DOS_TICK_HZ
        return max(0.0, min(1.0, accumulator / tick_dt))

    def render_interpolation_target(self, previous: tuple[float, float], current: tuple[float, float]) -> tuple[float, float]:
        """Linear fixed-tick target used by every render track.

        Both interpolation modes start from this same universal target; smooth
        mode only lets the displayed pose chase the target with a short
        framerate-independent filter.
        """
        alpha = self.render_interpolation_alpha(self._logic_accum)
        return lerp_point(previous, current, alpha)

    def presentation_point(
        self,
        key: Hashable,
        previous: tuple[float, float],
        current: tuple[float, float],
        *,
        rate_hz: float = 26.0,
        snap_distance: float = 48.0,
    ) -> tuple[float, float]:
        target = self.render_interpolation_target(previous, current)
        if not self.render_interpolation_smooth_enabled():
            return target
        smoother = getattr(self, "_presentation_smoother", None)
        if smoother is None:
            self._presentation_smoother = PresentationSmoother()
            smoother = self._presentation_smoother
        return smoother.point(
            key,
            target,
            dt=getattr(self, "_last_render_dt", 1.0 / 60.0),
            rate_hz=rate_hz,
            snap_distance=snap_distance,
        )

    @staticmethod
    def render_coord(value: float) -> int:
        # Use nearest-pixel snapping for interpolated render positions.  The old
        # int() floor biased every fractional step backwards, which creates an
        # uneven 0,0,1,1,2 cadence when the DOS tick movement is spread over
        # several Tk frames.  Rounding keeps the visual phase centered while all
        # gameplay remains on integer/fixed-tick coordinates.
        return int(math.floor(value + 0.5))

    def player_render_position(self) -> tuple[float, float]:
        if not self.visual_interpolation_enabled:
            return self.player.x, self.player.y
        return self.presentation_point(
            ("player", 0),
            self._prev_player_render_pos,
            (float(self.player.x), float(self.player.y)),
            rate_hz=30.0,
            snap_distance=64.0,
        )

    def entity_render_position(self, obj) -> tuple[float, float]:
        if not self.visual_interpolation_enabled or self.is_world_map:
            return float(obj.x), float(obj.y)
        old = self._prev_entity_render_pos.get(id(obj))
        if old is None:
            return float(obj.x), float(obj.y)
        # Actor slots and the player are advanced on the same fixed DOS clock.
        # Use the same target alpha and the same optional presentation filter;
        # otherwise a carried player and the moving platform under him can
        # drift by one render phase even when fixed-tick state is correct.
        return self.presentation_point(
            ("entity", id(obj)),
            old,
            (float(obj.x), float(obj.y)),
            rate_hz=30.0,
            snap_distance=64.0,
        )

    def capture_death_camera(self) -> None:
        # Called from PlayerLifecycleMixin.kill_player() before DS:69F5 is set.
        # It snapshots the current mission viewport registers for the separate
        # death-arc clamp and draw path.
        if self.is_world_map:
            self._death_camera = (int(self.world_camera_x), int(self.world_camera_y))
        else:
            self._death_camera = self.camera((self.player.x, self.player.y))

    def clear_death_camera(self) -> None:
        self._death_camera = None

    def mission_camera_target(self, player_pos: tuple[float, float]) -> tuple[float, float]:
        px, py = player_pos
        view_w, screen_h = self.viewport_size()
        view_h = max(1, screen_h - STATUS_BAR_H)
        max_x = max(0, LEVEL_W * TILE - view_w)
        max_y = max(0, LEVEL_H * TILE - view_h)
        x = min(max(px + PLAYER_W / 2 - view_w / 2, 0), max_x)
        y = min(max(py + PLAYER_H / 2 - view_h / 2, 0), max_y)
        return float(x), float(y)

    def camera(self, player_pos: tuple[float, float] | None = None) -> tuple[int, int]:
        death_camera = getattr(self, "_death_camera", None)
        if getattr(self, "player_dead_timer", 0) > 0 and death_camera is not None:
            return death_camera
        if self.is_world_map:
            if self.visual_interpolation_enabled:
                camera_pos = self.presentation_point(
                    ("camera", "world"),
                    self._prev_world_camera,
                    (float(self.world_camera_x), float(self.world_camera_y)),
                    rate_hz=22.0,
                    snap_distance=96.0,
                )
                return self.render_coord(camera_pos[0]), self.render_coord(camera_pos[1])
            return int(self.world_camera_x), int(self.world_camera_y)

        current_player = player_pos if player_pos is not None else (self.player.x, self.player.y)
        target = self.mission_camera_target(current_player)
        if self.visual_interpolation_enabled and self.render_interpolation_smooth_enabled():
            target = self.presentation_point(
                ("camera", "mission"),
                target,
                target,
                rate_hz=16.0,
                snap_distance=96.0,
            )
        return self.render_coord(target[0]), self.render_coord(target[1])

    def draw(self) -> None:
        current_phase = self.current_tile_anim_tick()
        if self.level_image is None or (not self.is_world_map and self._level_image_phase != current_phase):
            self.render_level_image_for_phase(current_phase)
        if self.level_image is None:
            return
        player_rx, player_ry = self.player_render_position()
        cam_x, cam_y = self.camera((player_rx, player_ry))
        view_w, screen_h = self.viewport_size()
        world_h = max(1, screen_h - STATUS_BAR_H)
        world_frame = self.level_image.crop((cam_x, cam_y, cam_x + view_w, cam_y + world_h))
        frame = Image.new("RGBA", (view_w, screen_h), (0, 0, 0, 255))
        frame.paste(world_frame, (0, 0))
        self.draw_fast_animated_tiles(frame, cam_x, cam_y)

        px = self.render_coord(player_rx - cam_x)
        py = self.render_coord(player_ry - cam_y)
        if self.is_world_map:
            self.draw_world_player(frame, px, py)
            self.draw_world_entrance_numbers(frame, cam_x, cam_y)
        else:
            # The main SAM1 frame path draws the player around 0x20CE..0x21E4,
            # then starts iterating actor slots from DS:6826 = 2 at 0x227E.
            # Normal static cells are baked into level_image underneath him.
            # The EXE has a +0x1CA-only redraw routine at d93:2530/0xFE60.
            # Composite static object/overlay cells after the player before
            # drawing runtime actor slots. This is independent of source BG/FG:
            # for example raw 0xEB is a BG cell but writes cA=0x02FC.
            self.draw_player_sprite(frame, px, py)
            if self.foreground_image is not None:
                fg = self.foreground_image.crop((cam_x, cam_y, cam_x + view_w, cam_y + world_h))
                frame.alpha_composite(fg)
            self.draw_teleporters(frame, cam_x, cam_y)
            self.draw_teleport_warp_effect(frame, cam_x, cam_y)
            self.draw_entities(frame, cam_x, cam_y)

        self.draw_status_bar(frame, view_w, screen_h)

        scaled_frame = frame.resize((view_w * self.zoom, screen_h * self.zoom), Image.Resampling.NEAREST) if self.zoom != 1 else frame

        # The canvas itself already has a black background, so there is no need
        # to allocate a second padded RGBA image just to cover unused space after
        # resizing.  Reuse the Tk image when the zoomed size is unchanged;
        # otherwise Tk spends most of the frame creating/configuring canvas
        # image objects instead of drawing the DOS framebuffer.
        if self.frame_photo is None or self._frame_photo_size != scaled_frame.size:
            self.frame_photo = ImageTk.PhotoImage(scaled_frame)
            self._frame_photo_size = scaled_frame.size
            if self._frame_canvas_item is None:
                self._frame_canvas_item = self.canvas.create_image(0, 0, image=self.frame_photo, anchor="nw")
            else:
                self.canvas.itemconfigure(self._frame_canvas_item, image=self.frame_photo)
        else:
            self.frame_photo.paste(scaled_frame)

    def current_tile_anim_tick(self) -> int:
        # Background codes 0x35..0x37 are static; only specific runtime draw
        # tiles have animation branches.  Do not use the raw DOS tick as the
        # static-image cache key: that forces a full level rerender every tick.
        # Encode only the phases that can actually change a baked tile.
        satellite_phase = (self.anim_ticks // 3) % 4
        beam_core_phase = (self.anim_ticks // 4) % 2
        # Raw 0x82 laser fields use the same 4-tick blink cadence while they
        # exist.  Once disabled they are permanently skipped and this phase no
        # longer causes redraw churn.
        laser_phase = beam_core_phase if not self.laser_field_deactivated else 0
        return (satellite_phase << 4) | (beam_core_phase << 1) | laser_phase

    def render_level_image_for_phase(self, anim_tick: int) -> None:
        renderer = SecretAgentRenderer(self.episode)
        skip_codes = set()
        skip_cells = set()
        if not self.is_world_map:
            # Dynamic objects are runtime actors. Do not leave their original raw
            # marker sprite baked into the static background; otherwise moving
            # platforms/enemies and the player are drawn twice. Runtime-removed
            # pickups/doors are skipped by exact visual cell identity.
            skip_codes = set(DYNAMIC_MISSION_CODES)
            # Raw 0x60 water is not a normal actor slot, but its translated
            # runtime visual 0x01F3 has a special draw-time two-cel branch in
            # the EXE.  Do not bake the raw static sprite into either cached
            # layer; draw_fast_animated_tiles() overlays the live phase so the
            # cached foreground cannot hide the animation.
            skip_codes.add(WATER_CODE)
            # Raw 0x77 is a composite runtime object: cA=0x00B3 on the
            # upper solid cell and cA=0x00B7 on the bottom pad.  Draw it live
            # so the upper bank-10 28/29 animation and the warp overlay can be
            # driven from fixed DOS ticks instead of being baked into the
            # static foreground cache.
            skip_codes.add(TELEPORTER_CODE)
            if not self.has_glasses:
                skip_codes.add(HIDDEN_PLATFORM_CODE)
            skip_cells = set(self.collected_cells) | set(self.opened_doors) | set(self.opened_exit_doors)
            if self.laser_field_deactivated or not self.laser_field_visible():
                skip_cells |= self.laser_field_source_keys()
        def is_static_front_cell(_x: int, _y: int, code: int, layer: str) -> bool:
            if code in (0, 0x20):
                return False
            if layer == "fg":
                return True
            return any(write.cA for write in runtime_cell_writes_for_code(code))

        if self.is_world_map:
            # Raw 0x59 is the island-map player start marker.  It is a
            # runtime spawn token, not a static world sprite; otherwise the
            # marker remains baked into the map and the live player is drawn
            # a second time after moving away.
            skip_codes.add(WORLD_PLAYER_CODE)
            skip_cells = set(self.completed_world_entrance_source_keys())
            self.foreground_image = None
            self.level_image = renderer.render(
                self.level_index,
                zoom=1,
                show_codes=self.show_codes,
                show_unknown=self.show_unknown,
                skip_codes=skip_codes,
                skip_cells=skip_cells,
                anim_tick=anim_tick,
            )
            self.draw_completed_world_entrance_overlays()
        else:
            self.level_image = renderer.render(
                self.level_index,
                zoom=1,
                show_codes=self.show_codes,
                show_unknown=self.show_unknown,
                show_bg=True,
                show_fg=False,
                skip_codes=skip_codes,
                skip_cells=skip_cells,
                anim_tick=anim_tick,
                cell_filter=lambda x, y, code, layer: not is_static_front_cell(x, y, code, layer),
            )
            self.foreground_image = renderer.render(
                self.level_index,
                zoom=1,
                show_codes=False,
                show_unknown=False,
                show_bg=True,
                show_fg=True,
                skip_codes=skip_codes,
                skip_cells=skip_cells,
                anim_tick=anim_tick,
                transparent_base=True,
                cell_filter=is_static_front_cell,
            )
            self.draw_open_exit_door_overlays()
        self._level_image_phase = anim_tick

    def draw_open_exit_door_overlays(self) -> None:
        """Draw the post-dynamite exit door state from the real 16x16 art.

        The original state-0x16 branch does not delete the door footprint.  It
        rewrites the lower runtime cell visual 0x027D to 0x027E, and rewrites
        the upper runtime cell from foreground visual 0x0279 into background/
        layer-B visual 0x027A.  Both cells have their collision byte cleared.
        In the decoded bank-5 art this is the two-tile broken/open door:
        top tile 33 and bottom tile 37.
        """
        if self.foreground_image is None or not self.opened_exit_doors:
            return
        top = self.episode.tiles16.get(5, 33)
        bottom = self.episode.tiles16.get(5, 37)
        if top is None or bottom is None:
            return
        for x, y, _code, _layer in self.opened_exit_doors:
            if 0 <= x < LEVEL_W and 0 <= y - 1 < LEVEL_H:
                self.foreground_image.alpha_composite(top, (x * TILE, (y - 1) * TILE))
            if 0 <= x < LEVEL_W and 0 <= y < LEVEL_H:
                self.foreground_image.alpha_composite(bottom, (x * TILE, y * TILE))

    def draw_teleporters(self, frame: Image.Image, cam_x: int, cam_y: int) -> None:
        if self.is_world_map:
            return
        top_ref = teleporter_top_tile(self.anim_ticks)
        pad_ref = teleporter_pad_tile()
        top_tile = self.episode.tiles16.get(*top_ref)
        pad_tile = self.episode.tiles16.get(*pad_ref)
        if top_tile is None and pad_tile is None:
            return
        view_w, screen_h = self.viewport_size()
        world_h = max(1, screen_h - STATUS_BAR_H)
        for cell in self.teleporter_cells():
            key = self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
            if key in self.collected_cells or key in self.opened_doors or key in self.opened_exit_doors:
                continue
            px = cell.x * TILE - cam_x
            py = cell.y * TILE - cam_y
            if top_tile is not None:
                self.alpha_composite_clipped(frame, top_tile, px, py - TILE, view_w, world_h)
            if pad_tile is not None:
                self.alpha_composite_clipped(frame, pad_tile, px, py, view_w, world_h)

    def draw_teleport_warp_effect(self, frame: Image.Image, cam_x: int, cam_y: int) -> None:
        if not self.teleport_active:
            return
        tile = self.episode.tiles16.get(*teleport_warp_tile(self.teleport_timer_ticks))
        if tile is None:
            return
        rx, ry = self.player_render_position()
        # SAM1:0x21E4..0x2254 uses the player draw coordinates (DS:34EE/F0)
        # and draws the bank-10 effect over the player during both halves of
        # the DS:69E2 countdown.
        frame.alpha_composite(tile, (self.render_coord(rx - cam_x), self.render_coord(ry - cam_y)))

    @staticmethod
    def alpha_composite_clipped(frame: Image.Image, tile: Image.Image, px: int, py: int, view_w: int, world_h: int) -> None:
        if px <= -tile.width or py <= -tile.height or px >= view_w or py >= world_h:
            return
        if 0 <= px and 0 <= py and px + tile.width <= view_w and py + tile.height <= world_h:
            frame.alpha_composite(tile, (px, py))
            return
        dst_x = max(0, px)
        dst_y = max(0, py)
        src_x = max(0, -px)
        src_y = max(0, -py)
        src_r = min(tile.width, view_w - dst_x + src_x)
        src_b = min(tile.height, world_h - dst_y + src_y)
        if src_r <= src_x or src_b <= src_y:
            return
        frame.alpha_composite(tile.crop((src_x, src_y, src_r, src_b)), (dst_x, dst_y))

    def draw_fast_animated_tiles(self, frame: Image.Image, cam_x: int, cam_y: int) -> None:
        # Raw 0x60 / runtime visual 0x01F3 has its own EXE draw branch that
        # alternates bank 4 tile 48 with the paired bank 4 tile 0 graphic.  The
        # previous static-layer cache only refreshed it on the slower baked-tile
        # phase, so overlay it from the fixed actor tick for the visibly faster
        # water cadence while keeping gameplay collision unchanged.
        if self.is_world_map:
            return
        water_tile_no = 48 if (self.anim_ticks & 1) == 0 else 0
        water_tile = self.episode.tiles16.get(4, water_tile_no)
        if water_tile is None:
            return
        view_w, screen_h = self.viewport_size()
        world_h = max(1, screen_h - STATUS_BAR_H)
        for cell in self.water_cells():
            key = self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
            if key in self.collected_cells or key in self.opened_doors or key in self.opened_exit_doors:
                continue
            px = cell.x * TILE - cam_x
            py = cell.y * TILE - cam_y
            self.alpha_composite_clipped(frame, water_tile, px, py, view_w, world_h)

    def draw_world_player(self, frame: Image.Image, px: int, py: int) -> None:
        # Level-0 draw path SAM1:0x20CE..0x21E4 uses DS:34EE/34F0 directly.
        # Earlier ports drew the world-map sprite at -2/-1 relative to the
        # gameplay origin, making the ASM 10x16 collision rect look too wide.
        self.draw_player_sprite(frame, px, py)

    def draw_player_sprite(self, frame: Image.Image, px: int, py: int, *, offset: tuple[int, int] = (0, 0)) -> None:
        if self.is_world_map:
            tile_ref = player_tile(state=self.player.anim_state, walk_counter=self.player.walk_counter)
        elif self.player_dead_timer > 0:
            # Player death uses the two dedicated bank-13 cels after the jump/air
            # cels.  Toggle them during the DS:69F6 countdown; do not freeze on
            # the last normal movement frame.
            tile_ref = (13, PLAYER_DEATH_TILES[(self.player_death_frame_counter // 4) & 1])
        else:
            tile_ref = player_tile(
                state=self.player.anim_state,
                walk_counter=self.player.walk_counter,
            )
        tile = self.episode.tiles16.get(*tile_ref)
        if tile:
            if not self.is_world_map:
                tile = self.apply_player_hurt_flash(tile)
            frame.alpha_composite(tile, (px + offset[0], py + offset[1]))
            return
        draw = ImageDraw.Draw(frame)
        draw.rectangle([px, py, px + PLAYER_W - 1, py + PLAYER_H - 1], fill=(255, 220, 64, 255), outline=(0, 0, 0, 255))

    def apply_player_hurt_flash(self, tile: Image.Image) -> Image.Image:
        # SAM1:0x20F8..0x216F decrements the DS:6A42 invulnerability counter
        # during the player draw path.  The initial hit starts a five-draw
        # bright pulse; countdown values 0x14 and 0x0A restart it.  Derive the
        # three pulse windows from the remaining timer so the transient visual
        # does not need a second independently updated runtime counter.
        remaining_ticks = math.ceil(self.hurt_flash * DOS_TICK_HZ)
        bright = remaining_ticks > 0x19 or 0x0F < remaining_ticks <= 0x14 or 0x05 < remaining_ticks <= 0x0A
        if not bright:
            return tile
        flashed = Image.new("RGBA", tile.size, (255, 255, 255, 0))
        flashed.putalpha(tile.getchannel("A"))
        return flashed

    def apply_enemy_hit_flash(self, tile: Image.Image, enemy: Enemy) -> Image.Image:
        # ASM evidence: every decoded non-lethal projectile-hit branch writes
        # DS:34CC = 3.  The sprite draw path first checks DS:34CC; while it is
        # positive it draws from an alternate bright/white cel source and
        # decrements DS:34CC after drawing.  The decoded PNG atlas does not keep
        # that transient white copy as a separate bank, so emulate the same
        # visible effect by replacing non-transparent sprite pixels with white
        # for those three draw passes.
        if enemy.hit_flash_ticks <= 0:
            return tile
        flashed = Image.new("RGBA", tile.size, (255, 255, 255, 0))
        alpha = tile.getchannel("A")
        flashed.putalpha(alpha)
        return flashed

    def draw_entities(self, frame: Image.Image, cam_x: int, cam_y: int) -> None:
        for platform in self.entities.platforms:
            rx, ry = self.entity_render_position(platform)
            self.draw_code_sprite(frame, platform.code, self.render_coord(rx - cam_x), self.render_coord(ry - cam_y))
        for barrel in self.entities.barrels:
            rx, ry = self.entity_render_position(barrel)
            self.draw_code_sprite(frame, barrel.code, self.render_coord(rx - cam_x), self.render_coord(ry - cam_y))
        for satellite in self.entities.satellites:
            tile = self.episode.tiles16.get(*satellite_tile(satellite.frame_index))
            if tile:
                tile = self.apply_enemy_hit_flash(tile, satellite)
                rx, ry = self.entity_render_position(satellite)
                frame.alpha_composite(tile, (self.render_coord(rx - cam_x), self.render_coord(ry - cam_y)))
        for enemy in self.entities.enemies:
            if enemy.code == 0x24:
                multi_refs = state27_actor_refs(
                    enemy.direction,
                    enemy.frame_counter,
                    walking_phase=(enemy.kind == "state27_shooter" and enemy.phase_ticks > 0),
                )
            elif enemy.code == 0x58:
                multi_refs = state1f_actor_refs(
                    enemy.direction,
                    enemy.frame_counter,
                    walking_phase=(enemy.kind == "state1f_shooter" and enemy.phase_ticks > 0),
                )
            else:
                multi_refs = multi_tile_actor_refs(enemy.code, enemy.direction, enemy.frame_counter)
            if multi_refs is not None:
                for relx, rely, bank, tile_no in multi_refs:
                    tile = self.episode.tiles16.get(bank, tile_no)
                    if tile:
                        if enemy.code in {0xAE, 0x24, 0x56, 0x63} and enemy.direction < 0:
                            tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                        tile = self.apply_enemy_hit_flash(tile, enemy)
                        rx, ry = self.entity_render_position(enemy)
                        frame.alpha_composite(tile, (self.render_coord(rx - cam_x + relx * TILE), self.render_coord(ry - cam_y + rely * TILE)))
                continue
            if enemy.bank == 14 and enemy.base_tile is not None:
                animated = bank14_guard_tile(enemy.base_tile, direction=enemy.direction, frame_counter=enemy.frame_counter)
            else:
                animated = walker_tile(enemy.code, direction=enemy.direction, anim_time=enemy.anim_time, frame_counter=enemy.frame_counter)
            if enemy.kind == "state2b_anim":
                rx, ry = self.entity_render_position(enemy)
                for relx, rely, bank, tile_no in state2b_actor_refs(enemy.frame_counter):
                    tile = self.episode.tiles16.get(bank, tile_no)
                    if tile:
                        tile = self.apply_enemy_hit_flash(tile, enemy)
                        frame.alpha_composite(tile, (self.render_coord(rx - cam_x + relx * TILE), self.render_coord(ry - cam_y + rely * TILE)))
                continue
            if enemy.kind == "state2c_anim":
                tile = self.episode.tiles16.get(*state2c_tile(enemy.code, enemy.frame_counter))
                if tile:
                    tile = self.apply_enemy_hit_flash(tile, enemy)
                    rx, ry = self.entity_render_position(enemy)
                    frame.alpha_composite(tile, (self.render_coord(rx - cam_x), self.render_coord(ry - cam_y)))
                    continue
            if enemy.kind == "state17_landmine":
                # State 0x17 was updating DS:34D6 correctly, but the renderer
                # fell through to draw_code_sprite(0x4D), i.e. the original
                # static map marker.  Use the object-id draw branch recovered
                # from SAM1:0x36C2..0x3725 / 0x3728..0x378E instead.
                tile = self.episode.tiles16.get(*state17_landmine_tile(enemy.object_id, enemy.frame_counter))
                if tile:
                    rx, ry = self.entity_render_position(enemy)
                    frame.alpha_composite(tile, (self.render_coord(rx - cam_x), self.render_coord(ry - cam_y)))
                    continue
            if enemy.kind == "state23_contact_bomb":
                # SAM1:0x9FED..0xA15E keeps raw 0x75 in the right-facing
                # 0x01..0x13 frame range and does not walk.  Do not fall back
                # to the generic direction-based walker renderer, which can
                # select bank2 tiles 12..15 and make the actor look like a
                # mirrored patrol enemy.
                tile = self.episode.tiles16.get(*state23_contact_bomb_tile(enemy.frame_counter))
                if tile:
                    tile = self.apply_enemy_hit_flash(tile, enemy)
                    rx, ry = self.entity_render_position(enemy)
                    frame.alpha_composite(tile, (self.render_coord(rx - cam_x), self.render_coord(ry - cam_y)))
                    continue
            if animated is not None:
                tile = self.episode.tiles16.get(*animated)
                if tile:
                    # Some special actors are stored as a single 4-frame family
                    # in the atlas and the EXE mirrors/draws them according to
                    # DS:34E2 rather than using a separate second 4-tile block.
                    # 0x6E was previously interpreted as bank2 32..35 + 36..39,
                    # but 36..39 are a separate blue actor family.  0x7F is the
                    # same pattern for bank5 8..11.
                    if enemy.code in {0x6E, 0x7F} and enemy.direction < 0:
                        tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                    tile = self.apply_enemy_hit_flash(tile, enemy)
                    rx, ry = self.entity_render_position(enemy)
                    frame.alpha_composite(tile, (self.render_coord(rx - cam_x), self.render_coord(ry - cam_y)))
                    continue
            rx, ry = self.entity_render_position(enemy)
            self.draw_code_sprite(frame, enemy.code, self.render_coord(rx - cam_x), self.render_coord(ry - cam_y))
        for spike in self.entities.spike_traps:
            tile_ref = spike_frame_for_timer(spike.kind, spike.timer_ticks)
            if tile_ref is not None:
                tile = self.episode.tiles16.get(*tile_ref)
                if tile:
                    frame.alpha_composite(tile, (self.render_coord(spike.x - cam_x), self.render_coord(spike.draw_y - cam_y)))
        for beam in self.entities.beam_traps:
            self.draw_beam_trap(frame, beam, cam_x, cam_y)
        draw = ImageDraw.Draw(frame)
        for shot in self.entities.projectiles:
            rx, ry = self.entity_render_position(shot)
            x = self.render_coord(rx - cam_x)
            y = self.render_coord(ry - cam_y)
            if shot.is_impact:
                if shot.impact_visible:
                    boom_frames = (24, 25, 26, 27)
                    impact_frame = min(len(boom_frames) - 1, shot.frame_counter // 3)
                    tile = self.episode.tiles16.get(5, boom_frames[impact_frame])
                    if tile:
                        frame.alpha_composite(tile, (x - 8, y - 8))
                continue
            if shot.anim_tiles:
                tile_no = shot.anim_tiles[(shot.frame_counter // 2) % len(shot.anim_tiles)]
            else:
                tile_no = shot.tile_right if shot.direction >= 0 else shot.tile_left
            tile = self.episode.tiles16.get(shot.bank, tile_no)
            if tile:
                draw_y = y if shot.life_ticks > 0 else y - 7
                frame.alpha_composite(tile, (x, draw_y))
            else:
                fill = (255, 96, 80, 255) if shot.hostile else (255, 255, 96, 255)
                draw.rectangle([x, y, x + 3, y + 1], fill=fill)
        for explosion in self.entities.explosions:
            # Player/guard bullet impact spark: decoded bank 5 tiles 24..27.
            boom_frames = (24, 25, 26, 27)
            tile = self.episode.tiles16.get(5, boom_frames[min(len(boom_frames) - 1, explosion.frame_counter // 3)])
            if tile:
                rx, ry = self.entity_render_position(explosion)
                frame.alpha_composite(tile, (self.render_coord(rx - cam_x), self.render_coord(ry - cam_y)))
        for popup in self.entities.score_popups:
            tile = self.episode.tiles16.get(10, popup.tile)
            if tile:
                rx, ry = self.entity_render_position(popup)
                frame.alpha_composite(tile, (self.render_coord(rx - cam_x), self.render_coord(ry - cam_y)))

    def draw_beam_trap(self, frame: Image.Image, beam: BeamTrap, cam_x: int, cam_y: int) -> None:
        # Bank 3 beam objects are not telescoping bars.  The static end pieces
        # stay put and only the middle discharge cel blinks while the timer is
        # active.  This corrects the earlier pass that animated the whole
        # 3-tile object in/out.
        phase = beam_phase_for_timer(beam.timer_ticks)
        flicker = 0 if phase is None else (beam.timer_ticks // 2) & 1
        if beam.kind == "vertical":
            refs: list[tuple[int, int, int, int]] = [
                (0, -2, 3, 27),  # ceiling/end cap
                (0, 0, 3, 26),   # base/end cap
                (0, -1, 3, 28 if phase is None else (29 + flicker)),
            ]
        else:
            refs = [
                (-2, 0, 3, 32),  # left/end cap
                (0, 0, 3, 33),   # right/end cap
                (-1, 0, 3, 34 if phase is None else (35 + flicker)),
            ]
        for relx, rely, bank, tile_no in refs:
            tile = self.episode.tiles16.get(bank, tile_no)
            if tile:
                rx, ry = self.entity_render_position(beam)
                frame.alpha_composite(tile, (self.render_coord(rx - cam_x + relx * TILE), self.render_coord(ry - cam_y + rely * TILE)))

    def draw_code_sprite(self, frame: Image.Image, code: int, px: int, py: int) -> None:
        from openagent.game_assets.mapping import TILE_MAP

        refs = TILE_MAP.get(code, [])
        for relx, rely, bank, tile_no in refs:
            tile = self.episode.tiles16.get(bank, tile_no)
            if tile:
                frame.alpha_composite(tile, (px + relx * TILE, py + rely * TILE))
