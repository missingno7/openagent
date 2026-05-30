from __future__ import annotations

import argparse
import math
import time
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

from .animation import (
    PLAYER_DEATH_TILES,
    PLAYER_FIRE_HOLD_SECONDS,
    PLAYER_STATE_FIRE_LEFT,
    PLAYER_STATE_FIRE_RIGHT,
    PLAYER_STATE_AIR_LEFT,
    PLAYER_STATE_AIR_RIGHT,
    PLAYER_STATE_IDLE_LEFT,
    PLAYER_STATE_IDLE_RIGHT,
    PLAYER_STATE_WALK_LEFT,
    PLAYER_STATE_WALK_RIGHT,
    PLAYER_WALK_COUNTER_MAX,
    PLAYER_WALK_COUNTER_START,
    PLAYER_WALK_COUNTER_STEP,
    player_tile,
    actor_walk_counter_next,
    state27_walk_counter_next,
    state27_actor_refs,
    state2a_dog_counter_next,
    walker_tile,
    bank14_guard_tile,
    satellite_tile,
    multi_tile_actor_refs,
    state2b_tile,
    state2c_tile,
    state17_landmine_tile,
)
from .collision import PLAYER_COLLISION_BOTTOM, PLAYER_DRAW_H, PLAYER_DRAW_W, player_body_probes
from .hud import HUDMixin, STATUS_BAR_H
from .entities import BeamTrap, Explosion, LevelEntities, MovingPlatform, Projectile, ScorePopup, extract_level_entities, Enemy, PushableBarrel
from .exe_actor_mechanics import (
    BANK14_GUARD_BEHAVIOUR_BY_BASE_TILE,
    BANK14_GUARD_SHOOT_TIMER_RANGE_BY_BASE_TILE,
    BANK14_GUARD_SPEED_BY_BASE_TILE,
    deterministic_range,
    object_id_is_shootable,
    spike_frame_for_timer,
    spike_is_dangerous,
    BEAM_CYCLE_TICKS,
    beam_phase_for_timer,
    beam_is_dangerous,
    SPIKE_CYCLE_TICKS,
    STATIONARY_SHOOTER_PROJECTILE,
    STATIONARY_SHOOTER_SPAWN_X_OFFSET,
    CEILING_LASER_PROJECTILE_BANK,
    CEILING_LASER_PROJECTILE_TILES,
    STATE27_PROJECTILE_BANK,
    STATE27_PROJECTILE_RIGHT_TILE,
    STATE27_PROJECTILE_LEFT_TILE,
    STATE27_OPEN_HELMET_SCORE,
    STATE1E_SHOOTER_CODE,
    STATE1F_SHOOTER_CODE,
    STATE1E_PROJECTILE_BANK,
    STATE1E_PROJECTILE_RIGHT_TILE,
    STATE1E_PROJECTILE_LEFT_TILE,
    STATE1F_PROJECTILE_BANK,
    STATE1F_PROJECTILE_RIGHT_TILE,
    STATE1F_PROJECTILE_LEFT_TILE,
    STATE1E_FIRE_COOLDOWN_TICKS,
    STATE23_CONTACT_BOMB_CODE,
    STATE23_CONTACT_BOMB_SCORE,
    STATE23_SHRAPNEL_BANK,
    STATE23_SHRAPNEL_RIGHT_TILE,
    STATE23_SHRAPNEL_LEFT_TILE,
    STATE24_UP_LASER_CODE,
    STATE24_UP_LASER_PROJECTILE_BANK,
    STATE24_UP_LASER_PROJECTILE_TILES,
    STATE2B_ANIM_CODE,
    STATE2B_ANIM_PERIOD,
    STATE2C_ANIM_PERIOD,
    STATE2C_CONTACT_HAZARD_CODE,
    STATE29_MONEY_BAG_IDLE_OBJECT_ID,
    STATE29_MONEY_BAG_FALLING_OBJECT_ID,
    STATE29_MONEY_BAG_SCORE,
    STATE29_MONEY_BAG_FALL_STEP_PX,
    STATE17_LANDMINE_CODE,
    STATE17_LANDMINE_IDLE_OBJECT_ID,
    STATE17_LANDMINE_TRIGGERED_OBJECT_ID,
    STATE17_LANDMINE_DAMAGE_FRAME,
)
from .exe_runtime_collision import runtime_cell_writes_for_code
from .level_model import build_runtime_collision_grid, cells_at, codes_at, iter_map_cells
from .loader import Campaign, ensure_editor_importable, load_campaign
from .player import Player
from .player_motion import advance_fall_tick, advance_jump_tick, horizontal_step_for_hold_ticks
from .player_lifecycle import PlayerLifecycleMixin
from .combat import CombatMixin
from .overworld import OverworldMixin
from .semantics import (
    ACTIVE_HIDDEN_PLATFORM_COLLISION_CODE,
    BANK14_GUARD_CODE_BY_BASE_TILE,
    BANK14_RIP_PICKUP_SCORE,
    BANK14_RIP_SHOT_SCORE,
    BANK14_RIP_TILE,
    GLASSES_CODE,
    HIDDEN_PLATFORM_CODE,
    LASER_FIELD_CODE,
    LASER_COMPUTER_CODE,
    FLOPPY_DISK_CODE,
    DYNAMITE_CODE,
    EXIT_DOOR_CODE,
    TELEPORTER_CODE,
    MISSION_PLAYER_START_CODE,
    door_unlocked_by,
    is_collectible_code,
    is_door_code,
    is_exit_door_code,
    is_dynamic_mission_code,
    is_mission_code_body_solid,
    is_mission_code_floor_solid,
    is_one_way_platform_code,
    mission_code_kind,
    score_popup_tile_for_value,
    score_value_for_code,
    STATIONARY_SHOOTER_CODES,
    PUSHABLE_BARREL_CODE,
)
from .sound import (
    SOUND_ENEMY_DEATH,
    SOUND_EXIT_DYNAMITE,
    SOUND_FALLING_BAG_DROP,
    SOUND_JUMP,
    SOUND_FIRE,
    SOUND_HURT,
    SOUND_NO_AMMO,
    SOUND_PLAYER_DEATH,
    SOUND_PICKUP,
    SOUND_SCORE_1000,
    SOUND_TELEPORT,
    SoundPlayer,
)

ROOT = Path(__file__).resolve().parents[1]
ensure_editor_importable(ROOT)

from secret_agent_editor.constants import LEVEL_H, LEVEL_W, ROW_BYTES, TILE
from secret_agent_editor.render import SecretAgentRenderer


from .game_constants import (
    ACTIVE_VIEW_H,
    ACTIVE_VIEW_W,
    DEFAULT_ZOOM,
    DOS_TICK_HZ,
    FALL_COUNTER_MAX,
    GAME_VIEW_H,
    GAME_VIEW_W,
    GROUND_EPSILON,
    HUD_H,
    JUMP_ASCENT_END_COUNTER,
    MAX_AMMO,
    MAX_ZOOM,
    MIN_ZOOM,
    PLAYER_H,
    PLAYER_VERTICAL_COUNTER_INITIAL,
    PLAYER_VERTICAL_STEP_TABLE,
    PLAYER_W,
    STARTING_AMMO,
    WORLD_MOVE_SPEED,
)

class OpenAgentApp(HUDMixin, PlayerLifecycleMixin, CombatMixin, OverworldMixin):
    def __init__(self, campaign: Campaign, *, episode: int = 1, level: int = 0, zoom: int = DEFAULT_ZOOM) -> None:
        self.campaign = campaign
        self.episode_numbers = campaign.episode_numbers
        self.episode_index = max(0, self.episode_numbers.index(episode) if episode in self.episode_numbers else 0)
        self.level_index = level
        self.player = Player()
        self.last_world_position: tuple[float, float] | None = None
        self.keys: set[str] = set()
        self.collision_enabled = True
        self.show_codes = False
        self.show_unknown = False
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, int(zoom)))
        self.canvas_w = GAME_VIEW_W * self.zoom
        self.canvas_h = GAME_VIEW_H * self.zoom
        self.level_image: Image.Image | None = None
        self.foreground_image: Image.Image | None = None
        self.level_photo: ImageTk.PhotoImage | None = None
        self.frame_photo: ImageTk.PhotoImage | None = None
        self.entities = LevelEntities([], [], [], [], [], [], [], [], [])
        self._ignore_barrel_collision: PushableBarrel | None = None
        self._ignore_barrel_collision_ticks = 0
        self.collected_cells: set[tuple[int, int, int, str]] = set()
        self.opened_doors: set[tuple[int, int, int, str]] = set()
        # Raw 0x71 exit doors do not disappear after the dynamite blast.
        # ASM state 0x16 scans runtime cells and rewrites only the lower
        # visual 0x027D to 0x027E. Keep these separate from generic opened
        # key doors, which are removed from the static map.
        self.opened_exit_doors: set[tuple[int, int, int, str]] = set()
        self.owned_keys: set[int] = set()
        self.score = 0
        self.ammo = STARTING_AMMO
        self.hurt_flash = 0.0
        # SAM1 initialises DS:6A40 to 3.  The generic hurt helper decrements
        # it and starts a short invulnerability/knockback phase; several hard
        # hazards skip that helper and set the death flag directly.
        self.lives = 3
        self.player_dead_timer = 0
        self.player_death_frame_counter = 0
        self.has_glasses = False
        self.has_floppy_disk = False
        self.has_dynamite = False
        # Raw 0x71 exit door / runtime visual 0x027D.  When dynamite is used,
        # the EXE spawns object 0x027B/state 0x16 with DS:34D8=0x28 before
        # the 0x027E/open-exit path can run.  Keep a per-source-cell countdown.
        self.exit_door_blast_timers: dict[tuple[int, int, int, str], int] = {}
        self.level_exit_pending = False
        self.laser_field_deactivated = False
        self.teleport_active = False
        self.teleport_timer_ticks = 0
        self.teleport_target: tuple[float, float] | None = None
        self.teleport_warped = False
        self.teleport_release_cell: tuple[int, int, str] | None = None
        self._teleporter_cells_cache: list | None = None
        self._laser_computer_last_warn_key: tuple[int, int, int, str] | None = None
        self._laser_field_source_keys_cache: set[tuple[int, int, int, str]] | None = None
        self._dynamic_source_keys_cache: set[tuple[int, int, int, str]] | None = None
        self._logic_accum = 0.0
        self._entity_accum = 0.0
        self._collision_grid_cache = None
        self._collision_grid_cache_key = None
        self.anim_ticks = 0
        self._level_image_phase: int | None = None
        self.last_tick = time.perf_counter()
        self.sound = SoundPlayer.from_campaign(campaign, self.episode_number)

        self.root = tk.Tk()
        self.root.title("OpenAgent")
        self.root.resizable(True, True)
        self.root.minsize(320, 240)
        self.canvas = tk.Canvas(self.root, width=self.canvas_w, height=self.canvas_h, highlightthickness=0, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_mousewheel)
        self.canvas.bind("<Control-Button-4>", lambda _event: self.change_zoom(1))
        self.canvas.bind("<Control-Button-5>", lambda _event: self.change_zoom(-1))
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)

        self.load_level(reset_player=True)

    @property
    def episode_number(self) -> int:
        return self.episode_numbers[self.episode_index]

    @property
    def episode(self):
        return self.campaign.bundle.episodes[self.episode_number]

    @property
    def level_count(self) -> int:
        return len(self.episode.levels)

    @property
    def is_world_map(self) -> bool:
        return self.level_index == 0

    def run(self) -> None:
        self.root.after(0, self.tick)
        self.root.mainloop()

    def close(self) -> None:
        self.sound.close()
        self.campaign.cleanup()
        self.root.destroy()

    def play_sound(self, sound_id: int) -> None:
        self.sound.play(sound_id)

    def on_key_press(self, event: tk.Event) -> None:
        key = event.keysym
        # Keyboard ISR SAM1:0x0079..0x0101 makes opposing movement flags
        # mutually exclusive at press time. Tk otherwise keeps both keysyms in
        # the set until their individual release events arrive, briefly turning
        # a direction change into "no movement" and resetting DS:681E.
        if key in {"Left", "a", "A"}:
            self.keys.difference_update({"Right", "d", "D"})
        elif key in {"Right", "d", "D"}:
            self.keys.difference_update({"Left", "a", "A"})
        elif key in {"Up", "w", "W"}:
            self.keys.difference_update({"Down", "s", "S"})
        elif key in {"Down", "s", "S"}:
            self.keys.difference_update({"Up", "w", "W"})
        self.keys.add(key)
        if key in {"Escape"}:
            self.close()
        elif key in {"r", "R"}:
            self.load_level(reset_player=True)
        elif key in {"e", "E"}:
            self.change_episode(1)
        elif key in {"q", "Q"}:
            self.change_episode(-1)
        elif key in {"Prior", "Next"}:
            self.change_level(1 if key == "Next" else -1)
        elif key in {"m", "M"}:
            self.level_index = 0
            self.load_level(reset_player=True)
        elif key in {"Return", "space"} and self.is_world_map:
            self.try_enter_world_level()
        elif key in {"c", "C"}:
            self.collision_enabled = not self.collision_enabled
        elif key in {"u", "U"}:
            self.show_unknown = not self.show_unknown
            self.load_level(reset_player=False)
        elif key in {"Tab"}:
            self.show_codes = not self.show_codes
            self.load_level(reset_player=False)
        elif key in {"plus", "KP_Add", "equal"}:
            self.change_zoom(1)
        elif key in {"minus", "KP_Subtract"}:
            self.change_zoom(-1)

    def on_key_release(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym)


    def on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas_w = max(1, int(event.width))
        self.canvas_h = max(1, int(event.height))

    def on_ctrl_mousewheel(self, event: tk.Event) -> None:
        self.change_zoom(1 if event.delta > 0 else -1)

    def change_zoom(self, delta: int) -> None:
        old = self.zoom
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom + delta))
        if self.zoom != old:
            view_w, view_h = self.viewport_size()
            self.root.geometry(f"{view_w * self.zoom}x{view_h * self.zoom}")
            self.draw()

    def viewport_size(self) -> tuple[int, int]:
        # Canvas pixels are output pixels.  Divide by zoom to get original DOS
        # logical pixels.  The default 320x200 at 2x mirrors the game viewport,
        # while resizing the window shows a larger/smaller camera crop.
        logical_w = max(160, self.canvas_w // max(1, self.zoom))
        logical_h = max(STATUS_BAR_H + 80, self.canvas_h // max(1, self.zoom))
        return logical_w, logical_h

    def change_episode(self, delta: int) -> None:
        self.episode_index = (self.episode_index + delta) % len(self.episode_numbers)
        self.level_index = min(self.level_index, self.level_count - 1)
        self.sound.load_episode(self.campaign, self.episode_number)
        self.load_level(reset_player=True)

    def change_level(self, delta: int) -> None:
        self.level_index = (self.level_index + delta) % self.level_count
        self.load_level(reset_player=True)

    def load_level(self, *, reset_player: bool) -> None:
        self.teleport_release_cell = None
        self.entities = LevelEntities([], [], [], [], [], [], [], [], []) if self.is_world_map else extract_level_entities(self.episode.levels[self.level_index])
        self._ignore_barrel_collision = None
        self._ignore_barrel_collision_ticks = 0
        if reset_player and not self.is_world_map:
            self.collected_cells.clear()
            self.opened_doors.clear()
            self.opened_exit_doors.clear()
            self.owned_keys.clear()
            self.score = 0
            self.ammo = STARTING_AMMO
            self.lives = 3
            self.player_dead_timer = 0
            self.hurt_flash = 0.0
            self.has_glasses = False
            self.has_floppy_disk = False
            self.has_dynamite = False
            self.exit_door_blast_timers.clear()
            self.level_exit_pending = False
            self.laser_field_deactivated = False
            self.reset_teleport_state()
            self._laser_computer_last_warn_key = None
            self._laser_field_source_keys_cache = None
            self._dynamic_source_keys_cache = None
            self.anim_ticks = 0
        if reset_player:
            if self.is_world_map:
                self.reset_teleport_state()
                spawn = self.last_world_position or self.find_world_spawn()
                self.player = Player(spawn[0], spawn[1])
            else:
                self.player = Player(*self.find_spawn())
        # Re-render after gameplay state has been reset.  This matters for
        # hidden platforms, collected cells and animated tile phase cache.
        self.rebuild_level_image()
        self.last_tick = time.perf_counter()
        self.draw()

    def rebuild_level_image(self) -> None:
        self._collision_grid_cache = None
        self._collision_grid_cache_key = None
        self._level_image_phase = None
        self.foreground_image = None
        self._teleporter_cells_cache = None
        self.render_level_image_for_phase(self.current_tile_anim_tick())

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
            skip_codes = {code for code in range(256) if is_dynamic_mission_code(code)}
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

    def find_spawn(self) -> tuple[float, float]:
        info = self.episode.levels[self.level_index]
        for cell in iter_map_cells(info):
            if cell.code == MISSION_PLAYER_START_CODE:
                return float(cell.x * TILE + 2), float(cell.y * TILE + 1)
        for y in range(3, LEVEL_H - 2):
            for x in range(2, LEVEL_W - 2):
                if not self.cell_solid(x, y) and self.cell_solid(x, y + 1):
                    return float(x * TILE + 2), float(y * TILE + 1)
        return 32.0, 32.0

    def iter_visual_codes(self, level_index: int):
        for cell in iter_map_cells(self.episode.levels[level_index]):
            yield cell.x, cell.y, cell.code

    def tick(self) -> None:
        now = time.perf_counter()
        dt = min(now - self.last_tick, 1 / 20)
        self.last_tick = now
        if self.player_dead_timer > 0:
            # DS:69F5/DS:69F6 death state keeps the actor draw path alive while
            # the countdown runs; the original alternates the player death cels
            # instead of freezing the whole game on the last normal frame.
            self.player_death_frame_counter += 1
            self.player_dead_timer -= 1
            if self.player_dead_timer <= 0:
                self.respawn_after_death()
        elif not self.is_world_map:
            self.update_barrel_overlap_state()
            self.update_exit_door_blasts()
        if self.player_dead_timer <= 0:
            if self.is_world_map:
                self.update_world_player(dt)
            else:
                self.update_entities(dt)
                self.update_player(dt)
                self.update_player_interactions(dt)
        self.draw()
        self.root.after(16, self.tick)

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
        return list(self._teleporter_cells_cache)

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

    def player_centered_on_teleporter(self, cell) -> bool:
        # ASM dispatcher compares the active runtime visual 0x00B7 and requires
        # the player coordinate to be very close to the tile-aligned pad before
        # setting DS:69E0.  Keep a small tolerance so keyboard/controller motion
        # can actually land on the same DOS condition.
        p = self.player
        center_x = p.x + PLAYER_W / 2
        center_y = p.y + PLAYER_H / 2
        pad_cx = cell.x * TILE + TILE / 2
        pad_cy = cell.y * TILE + TILE / 2
        return abs(center_x - pad_cx) <= 8 and abs(center_y - pad_cy) <= 12

    def update_teleport_release_gate(self) -> None:
        # The EXE keeps DS:69E0 non-zero throughout the warp and the input/warp
        # state does not immediately re-enter the dispatcher on the destination
        # pad.  Mirror that behaviour explicitly: after a warp, require the
        # player to step off the destination teleporter before another touch can
        # arm.  This prevents an endless A<->B ping-pong while standing still.
        if self.teleport_release_cell is None:
            return
        for cell in self.teleporter_cells():
            if (cell.x, cell.y, cell.layer) == self.teleport_release_cell:
                if self.player_centered_on_teleporter(cell):
                    return
                break
        self.teleport_release_cell = None

    def find_partner_teleporter(self, source_cell):
        for cell in self.teleporter_cells():
            if (cell.x, cell.y, cell.layer) != (source_cell.x, source_cell.y, source_cell.layer):
                return cell
        return None

    def choose_teleport_target_position(self, target_cell) -> tuple[float, float]:
        # EXE stores ((col-1)<<4, (row-1)<<4), then nudges X by +/-3 based on a
        # body-collision probe at the destination.  The decoded map model uses
        # zero-based cell coordinates, so target_cell.x/y already correspond to
        # the final pixel cell origin.
        base_x = float(target_cell.x * TILE)
        base_y = float(target_cell.y * TILE)
        candidates = [(base_x - 3, base_y), (base_x + 3, base_y), (base_x, base_y)]
        clear = self.world_player_body_clear_at if self.is_world_map else self.mission_player_body_clear_at
        for x, y in candidates:
            if 0 <= x <= LEVEL_W * TILE - PLAYER_W and 0 <= y <= LEVEL_H * TILE - PLAYER_H and clear(x, y):
                return x, y
        return base_x, base_y

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
            if not self.player_centered_on_teleporter(cell):
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
                self.last_world_position = (self.player.x, self.player.y)
        if self.teleport_timer_ticks <= -0x13:
            self.reset_teleport_state()
        return True

    def update_world_player(self, dt: float) -> None:
        p = self.player
        if self.update_teleport_tick():
            self.last_world_position = (p.x, p.y)
            return
        left = any(k in self.keys for k in ("Left", "a", "A"))
        right = any(k in self.keys for k in ("Right", "d", "D"))
        up = any(k in self.keys for k in ("Up", "w", "W"))
        down = any(k in self.keys for k in ("Down", "s", "S"))
        self.move_world_axis((right - left) * WORLD_MOVE_SPEED * dt, 0.0)
        self.move_world_axis(0.0, (down - up) * WORLD_MOVE_SPEED * dt)
        self.check_teleporter_touch()
        self.last_world_position = (p.x, p.y)

    def update_player(self, dt: float) -> None:
        # Keep the mission player on DOS-like fixed ticks.  The previous
        # continuous vy/gravity approximation could move by a fractional amount,
        # resolve by a while loop, then sample the same one-way tile again and
        # appear to fall through or freeze.
        self._logic_accum = min(self._logic_accum + dt, 0.15)
        while self._logic_accum >= 1.0 / DOS_TICK_HZ:
            self._logic_accum -= 1.0 / DOS_TICK_HZ
            self.update_player_tick()

    def update_player_tick(self) -> None:
        p = self.player
        if self.update_teleport_tick():
            p.move_hold_ticks = 0
            p.walk_time = 0.0
            p.walk_counter = PLAYER_WALK_COUNTER_START
            return
        left = any(k in self.keys for k in ("Left", "a", "A"))
        right = any(k in self.keys for k in ("Right", "d", "D"))
        jump = "space" in self.keys
        fire = any(k in self.keys for k in ("Control_L", "Control_R", "Control"))

        move_dir = (1 if right else 0) - (1 if left else 0)
        moving = move_dir != 0
        if moving:
            p.facing = 1 if move_dir > 0 else -1
            p.last_move_dir = move_dir
            p.move_hold_ticks += 1
            p.walk_counter += PLAYER_WALK_COUNTER_STEP
            if p.walk_counter > PLAYER_WALK_COUNTER_MAX:
                p.walk_counter = PLAYER_WALK_COUNTER_START
        else:
            p.move_hold_ticks = 0
            p.last_move_dir = 0
            p.walk_time = 0.0
            p.walk_counter = PLAYER_WALK_COUNTER_START

        p.fire_cooldown = max(0.0, p.fire_cooldown - 1.0 / DOS_TICK_HZ)
        p.firing_time = max(0.0, p.firing_time - 1.0 / DOS_TICK_HZ)
        # EXE fire key branch sets DS:3500 to 0x0B/0x0C only after a shot slot
        # is actually allocated.  If there is no ammo, or while DS:6EC1 jump is
        # active, it plays/skips without changing the pose.  On key release it
        # restores 0x09/0x0A.
        if fire and not p.fire_held:
            p.fire_pose_active = self.try_fire_projectile()
            if p.fire_pose_active:
                p.firing_time = PLAYER_FIRE_HOLD_SECONDS
        elif not fire:
            p.fire_pose_active = False
        p.fire_held = bool(fire)

        if moving:
            blocked = self.move_player_horizontal_tick(move_dir * horizontal_step_for_hold_ticks(p.move_hold_ticks))
            if blocked:
                # The full-step collision probe at SAM1:0xB7D9 resets DS:681E
                # once a blocked horizontal move is detected.
                p.move_hold_ticks = 0

        # SAM1:0xBC0E first calls the B8B3 fall pass whenever DS:6EC1 is clear.
        # This also runs while standing: landing does not clear DS:34EA, so a
        # later ledge fall starts from the capped terminal table index.
        if p.jump_anim_timer <= 0:
            p.fall_ticks, fall_step = advance_fall_tick(p.fall_ticks)
            self.move_player_fall_tick(fall_step)
            if jump and p.grounded:
                p.grounded = False
                p.fall_ticks = 0
                p.jump_anim_timer = 1
                # SAM1:0xBCE4 pushes sound 0x01 immediately before setting
                # DS:6EC1=1 and DS:34EA=0 for the table-driven jump phase.
                self.play_sound(SOUND_JUMP)

        if p.jump_anim_timer > 0:
            # EXE DS:6EC1 jump phase.  Use the same DS:34AF table as falling,
            # but subtract the displacement from Y.  At counter 0x0A the EXE
            # clears DS:6EC1 and keeps DS:34EA at 9, making the next fall tick
            # use table[10] rather than restarting from a fast 8px step.
            p.fall_ticks, jump_active, jump_step = advance_jump_tick(p.fall_ticks)
            p.jump_anim_timer = int(jump_active)
            if jump_step:
                blocked = self.move_player_upward_tick(jump_step)
                if blocked:
                    p.jump_anim_timer = 0
                    p.fall_ticks = JUMP_ASCENT_END_COUNTER - 1
        self.update_player_anim_state(moving=moving)

        max_x = LEVEL_W * TILE - PLAYER_W
        max_y = LEVEL_H * TILE - PLAYER_H
        p.x = min(max(p.x, 0), max_x)
        if p.y > max_y:
            p.y = float(max_y)
            p.vy = 0
            p.grounded = True
            p.jump_anim_timer = 0
            p.fall_ticks = FALL_COUNTER_MAX
            self.update_player_anim_state(moving=moving)

    def update_entities(self, dt: float) -> None:
        # Actor frame counters and simple walker motion are tick based in the
        # EXE.  Updating them at the 60Hz Tk redraw cadence made enemy animation
        # far too fast compared with the player, so keep them on the same DOS
        # tick clock.  Projectiles stay continuous for now because their EXE slot
        # update is still only partially mapped.
        self._entity_accum = min(self._entity_accum + dt, 0.15)
        while self._entity_accum >= 1.0 / DOS_TICK_HZ:
            self._entity_accum -= 1.0 / DOS_TICK_HZ
            self.anim_ticks += 1
            self.update_entities_tick()
        # Projectile actors are normal EXE actor slots too. Advance them in
        # the fixed actor tick loop, not continuously per Tk redraw frame.

    def update_entities_tick(self) -> None:
        dt = 1.0 / DOS_TICK_HZ
        for spike in self.entities.spike_traps:
            spike.timer_ticks += 1
            if spike.timer_ticks >= SPIKE_CYCLE_TICKS:
                spike.timer_ticks = 0
        for beam in self.entities.beam_traps:
            beam.timer_ticks += 1
            if beam.timer_ticks >= BEAM_CYCLE_TICKS:
                beam.timer_ticks = 0
        for satellite in self.entities.satellites:
            satellite.timer_ticks += 1
            if satellite.timer_ticks >= satellite.period_ticks:
                satellite.timer_ticks = 0
                satellite.frame_index = (satellite.frame_index + 1) % 4
        for platform in self.entities.platforms:
            carry_player = self.platform_below() is platform and self.player.grounded
            old_x = platform.x
            # Original actors use DS:34E6 as a literal per-tick pixel step.
            dx = platform.direction * platform.step_px
            platform.x += dx
            if self.platform_collides(platform):
                platform.x = old_x
                platform.direction *= -1
            elif carry_player:
                self.player.x += platform.x - old_x

        for enemy in self.entities.enemies:
            enemy.anim_time += dt
            if enemy.hit_flash_ticks > 0:
                enemy.hit_flash_ticks -= 1
            if enemy.is_rip:
                continue
            if enemy.kind == "state29_money_bag":
                # State 0x29 / raw 0x5B: idle object 0x01B3 is a trigger.
                # A tight player overlap rewrites the actor to falling object
                # 0x026B.  The moving branch advances down in 4px chunks until
                # collision, and a later tight overlap awards 0x1388 points.
                if enemy.object_id == STATE29_MONEY_BAG_IDLE_OBJECT_ID:
                    if self.money_bag_tight_overlap(enemy):
                        self.arm_money_bag_drop(enemy)
                    continue
                if enemy.object_id == STATE29_MONEY_BAG_FALLING_OBJECT_ID:
                    if self.money_bag_tight_overlap(enemy):
                        self.collect_money_bag_actor(enemy)
                        continue
                    old_y = enemy.y
                    enemy.y += STATE29_MONEY_BAG_FALL_STEP_PX
                    if self.enemy_collides(enemy) or enemy.y + TILE > LEVEL_H * TILE:
                        enemy.y = old_y
                        # The EXE keeps drawing/clearing this actor after the
                        # blocked branch; stopping it prevents tunnelling while
                        # preserving the pickup overlap.
                    continue
            if enemy.kind == "stationary_shooter":
                # EXE states 0x0A..0x0D do not walk.  They increment DS:34DA,
                # compare it to DS:34D8, then check same tile row and whether
                # the player is in front before calling projectile helper 0x5784.
                if enemy.alert_ticks > 0:
                    enemy.alert_ticks -= 1
                if self.rect_in_active_viewport(enemy.x, enemy.y, TILE, TILE) and self.enemy_can_see_player(enemy):
                    enemy.shoot_timer_ticks -= 1
                    if enemy.shoot_timer_ticks <= 0:
                        enemy.shoot_timer_ticks = enemy.shoot_interval_ticks
                        self.spawn_enemy_projectile(enemy)
                else:
                    enemy.shoot_timer_ticks = min(enemy.shoot_timer_ticks + 1, enemy.shoot_interval_ticks)
                continue
            if enemy.kind == "state24_up_laser":
                # State 0x24 / object 0x0071 is not a walking enemy.  It keeps
                # its X fixed, charges DS:34DA up to DS:34DC=10, and emits an
                # upward object-0x72 laser when the player is above and centered.
                period = max(1, enemy.shoot_interval_ticks or 10)
                enemy.shoot_timer_ticks = min(enemy.shoot_timer_ticks + 1, period)
                if enemy.shoot_timer_ticks >= period:
                    if self.enemy_can_see_player(enemy):
                        self.spawn_enemy_projectile(enemy)
                        enemy.shoot_timer_ticks = 0
                    else:
                        enemy.shoot_timer_ticks = period
                continue
            if enemy.kind == "state17_landmine":
                if enemy.object_id == STATE17_LANDMINE_IDLE_OBJECT_ID:
                    # Raw 0x4D is runtime object 0x0270 until touched.  The draw
                    # path at SAM1:0x36C2..0x3725 selects the visual by
                    # floor(DS:34D6 / 5), and the state-0x17 update wraps
                    # non-0x0271 objects once DS:34D6 > 9.  That yields exactly
                    # two idle/blinking cels, not a longer explosion sequence.
                    enemy.frame_counter += 1
                    if enemy.frame_counter > 9:
                        enemy.frame_counter = 1
                    if self.enemy_overlaps_player(enemy):
                        # SAM1:0xD0B1..0xD21E is more immediate than the old
                        # approximation: touching object 0x0270 clears the map
                        # cell, allocates object 0x0271/state 0x17, and then in
                        # the same branch sets DS:69F5=1/DS:69F6=0x23 unless
                        # the protection flag DS:69F3 is active.  The later
                        # state-0x17 frame-0x0B helper is the explosion/contact
                        # pass, not the first moment the player dies.
                        enemy.object_id = STATE17_LANDMINE_TRIGGERED_OBJECT_ID
                        enemy.frame_counter = 1
                        enemy.aux_ticks = 0
                        self.collected_cells |= {
                            self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
                            for cell in iter_map_cells(self.episode.levels[self.level_index])
                            if cell.code == STATE17_LANDMINE_CODE and cell.x == int(enemy.x) // TILE and cell.y == int(enemy.y) // TILE
                        }
                        self.kill_player()
                    continue
                enemy.frame_counter += 1
                if enemy.frame_counter == STATE17_LANDMINE_DAMAGE_FRAME and self.enemy_overlaps_player(enemy) and self.hurt_flash <= 0:
                    # The state-0x17 update still calls helper 0x53C4 at
                    # DS:34D6 == 0x0B.  Keep it as a secondary hard-death check
                    # for cases where the spawned explosion overlaps the player
                    # after the initial trigger path.
                    self.kill_player()
                if enemy.frame_counter == STATE17_LANDMINE_DAMAGE_FRAME + 1:
                    self.spawn_projectile_explosion(enemy.x + TILE / 2, enemy.y + TILE / 2)
                    self.spawn_projectile_explosion(enemy.x - TILE / 2, enemy.y + TILE / 2)
                    self.spawn_projectile_explosion(enemy.x + TILE * 1.5, enemy.y + TILE / 2)
                if enemy.frame_counter > 0x18:
                    if enemy in self.entities.enemies:
                        self.entities.enemies.remove(enemy)
                    continue
                continue
            if enemy.kind == "state2b_anim":
                # SAM1:0xB599..0xB5FC.  Period DS:34DA=5; after each period
                # advance DS:34D6 and wrap 0x14.. to random(5)+1.
                period = max(1, enemy.shoot_interval_ticks or STATE2B_ANIM_PERIOD)
                enemy.shoot_timer_ticks += 1
                if enemy.shoot_timer_ticks >= period:
                    enemy.shoot_timer_ticks = 0
                    enemy.frame_counter += 1
                    if enemy.frame_counter > 0x13:
                        enemy.frame_counter = deterministic_range(enemy.code, int(enemy.x)//TILE, int(enemy.y)//TILE, 1, 5, salt=self.anim_ticks)
                continue
            if enemy.kind == "state2c_anim":
                # SAM1:0xB5FE..0xB65D.  State 0x2C advances its frame counter
                # every actor tick; object 0x0103 also invokes helper 0x53C4,
                # a narrow player-contact hazard check.
                enemy.frame_counter += 2 if enemy.code == STATE2C_CONTACT_HAZARD_CODE else 1
                if enemy.frame_counter > 0x13:
                    enemy.frame_counter = 1
                if enemy.code == STATE2C_CONTACT_HAZARD_CODE and self.enemy_overlaps_player(enemy) and self.hurt_flash <= 0:
                    self.hurt_player()
                continue
            if enemy.kind == "state27_shooter":
                # SAM1:0xA89F..0xAFBF. Raw 0x24 is a helmet actor with two
                # private timers, not a plain continuously-walking shooter:
                #   DS:34DA increments to DS:34D8=0x3C before each shot test.
                #   DS:34DE is a walking/closed phase timer, init random(20)+60.
                #   DS:34DC is a short stationary/open hold, init 3 then 0x1E.
                # While DS:34DE is non-zero the actor walks and wraps its frame
                # range; when it reaches zero it stays still and clamps at the
                # end of its helmet/open frame range until DS:34DC refills DE.
                period = max(1, enemy.shoot_interval_ticks or 0x3C)
                enemy.shoot_timer_ticks += 1
                if enemy.shoot_timer_ticks >= period:
                    enemy.shoot_timer_ticks = 0
                    if self.enemy_can_see_player(enemy):
                        self.spawn_enemy_projectile(enemy)

                if enemy.phase_ticks > 0:
                    enemy.phase_ticks -= 1
                    if enemy.phase_ticks == 1:
                        # EXE sets DS:34DC=0x1E at the one-before-open tick.
                        enemy.aux_ticks = 0x1E
                        enemy.frame_counter = state27_walk_counter_next(enemy.frame_counter, direction=enemy.direction, walking_phase=False)
                        continue
                    old_x = enemy.x
                    enemy.x += enemy.direction * enemy.step_px
                    blocked = self.enemy_collides(enemy) or not self.enemy_has_floor_ahead(enemy)
                    if blocked:
                        enemy.x = old_x
                        enemy.direction *= -1
                        enemy.frame_counter = state27_walk_counter_next(0, direction=enemy.direction, walking_phase=True)
                    else:
                        enemy.frame_counter = state27_walk_counter_next(enemy.frame_counter, direction=enemy.direction, walking_phase=True)
                else:
                    enemy.frame_counter = state27_walk_counter_next(enemy.frame_counter, direction=enemy.direction, walking_phase=False)
                    enemy.aux_ticks -= 1
                    if enemy.aux_ticks <= 0:
                        enemy.phase_ticks = 0x50
                        enemy.aux_ticks = 0x1E
                if self.enemy_overlaps_player(enemy) and self.hurt_flash <= 0:
                    self.hurt_player()
                continue
            enemy.frame_counter = (
                state2a_dog_counter_next(enemy.frame_counter, direction=enemy.direction)
                if enemy.code == 0xAE
                else actor_walk_counter_next(enemy.frame_counter, direction=enemy.direction)
            )
            old_x = enemy.x
            if enemy.kind != "lightning_flyer" or enemy.alert_ticks <= 0:
                enemy.x += enemy.direction * enemy.step_px
            if enemy.kind == "ceiling_laser":
                # State 0x21 probes the collision table before accepting the
                # horizontal step.  Keep the crawler attached to its ceiling
                # track by checking the candidate position, not the old one.
                # This prevents a one-tile overrun past the last block above.
                blocked = (
                    self.enemy_collides(enemy)
                    or enemy.x < 0
                    or enemy.x + TILE > LEVEL_W * TILE
                    or not self.enemy_has_ceiling_track(enemy)
                )
            elif enemy.kind == "swimmer":
                # Shark/water swimmers use the same actor counter, but do not
                # need a floor probe. They reverse on body collision/level edge.
                blocked = self.enemy_collides(enemy) or enemy.x < 0 or enemy.x + TILE > LEVEL_W * TILE
            elif enemy.kind == "state06_contact_floater":
                # State 0x06 / raw 0x7F probes body collision at the candidate
                # side/top-bottom samples and reverses; unlike normal walkers
                # there is no floor-ahead support test, so it can patrol across
                # gaps instead of turning at ledges.
                blocked = self.enemy_collides(enemy) or enemy.x < 0 or enemy.x + TILE > LEVEL_W * TILE
            elif enemy.kind == "lightning_flyer":
                blocked = self.enemy_collides(enemy) or enemy.x < 0 or enemy.x + TILE > LEVEL_W * TILE
            else:
                blocked = self.enemy_collides(enemy) or not self.enemy_has_floor_ahead(enemy)
            if blocked:
                enemy.x = old_x
                enemy.direction *= -1
                enemy.frame_counter = (
                    state2a_dog_counter_next(0, direction=enemy.direction)
                    if enemy.code == 0xAE
                    else actor_walk_counter_next(0, direction=enemy.direction)
                )
            if enemy.kind == "state1e_shooter":
                # State 0x1E / raw 0x56 uses a countdown-style DS:34DA.
                # When it reaches zero and the player is on the same row in
                # the facing direction, helper 0x5784 is called with object
                # 0x0339, speed=4.  The EXE then reloads DS:34DA with 0x46.
                if enemy.shoot_timer_ticks > 0:
                    enemy.shoot_timer_ticks -= 1
                if enemy.shoot_timer_ticks <= 0 and self.enemy_can_see_player(enemy):
                    self.spawn_enemy_projectile(enemy)
                    enemy.shoot_timer_ticks = STATE1E_FIRE_COOLDOWN_TICKS
            elif enemy.kind == "state1f_shooter":
                # State 0x1F / raw 0x58 increments DS:34DA up to the spawn
                # table period (60), then emits object 0x033B if the same
                # facing/row gate passes.
                period = max(1, enemy.shoot_interval_ticks or 60)
                enemy.shoot_timer_ticks = min(enemy.shoot_timer_ticks + 1, period)
                if enemy.shoot_timer_ticks >= period:
                    if self.enemy_can_see_player(enemy):
                        self.spawn_enemy_projectile(enemy)
                        enemy.shoot_timer_ticks = 0
                    else:
                        enemy.shoot_timer_ticks = period
            if enemy.kind == "state06_contact_floater":
                # Helper 0x53C4 is invoked unconditionally by state 0x06 after
                # the movement/collision probe, which matches a contact hazard
                # rather than a passive decorative walker.
                if self.enemy_overlaps_player(enemy) and self.hurt_flash <= 0:
                    self.hurt_player()
                continue
            if enemy.kind == "state23_contact_bomb":
                # State 0x23 decrements DS:34DC only while the actor/player
                # contact helper reports overlap.  After three such actor ticks
                # it rewrites itself to explosion state and spawns side shots.
                if self.enemy_overlaps_player(enemy):
                    enemy.alert_ticks = enemy.alert_ticks or 3
                    enemy.alert_ticks -= 1
                    if enemy.alert_ticks <= 0:
                        self.explode_contact_bomb(enemy)
                        continue
                else:
                    enemy.alert_ticks = 0
            if enemy.kind == "lightning_flyer":
                # State 0x26 / raw 0x6E uses two timers:
                #   DS:34DE = pause/hold timer. While non-zero, the candidate
                #              X is discarded, so the actor animates but does
                #              not actually advance.
                #   DS:34DA = active lightning timer. When it is zero, the EXE
                #              immediately calls helper 0x5784 with object 0x89
                #              at (actor_x, actor_y + 16), then increments it.
                #              When it reaches DS:34D8, it resets to zero and
                #              reloads DS:34DE = 0x6E.
                if enemy.alert_ticks > 0:
                    enemy.alert_ticks -= 1
                    continue
                period = max(1, enemy.shoot_interval_ticks)
                if enemy.shoot_timer_ticks == 0:
                    self.spawn_lightning_bolt(enemy)
                enemy.shoot_timer_ticks += 1
                if enemy.shoot_timer_ticks >= period:
                    enemy.shoot_timer_ticks = 0
                    enemy.alert_ticks = 0x6E
                continue
            if enemy.alert_ticks > 0:
                enemy.alert_ticks -= 1
            if enemy.kind == "ceiling_laser" and enemy.can_shoot:
                # SAM1:0x9A25 increments DS:34DA.  At DS:34DA == DS:34D8 it
                # tests whether the player is in the 32px-wide column below the
                # crawler.  If the test fails, SAM1:0x9AB2 decrements the timer
                # back to period-1, so the shooter remains armed and fires on
                # the first valid tick after the player walks underneath.
                period = max(1, enemy.shoot_interval_ticks)
                enemy.shoot_timer_ticks = min(enemy.shoot_timer_ticks + 1, period)
                if enemy.shoot_timer_ticks >= period:
                    if self.enemy_can_see_player(enemy):
                        self.spawn_enemy_projectile(enemy)
                        enemy.shoot_timer_ticks = 0
                    else:
                        enemy.shoot_timer_ticks = period - 1
                continue
            if enemy.can_shoot:
                if self.enemy_can_see_player(enemy):
                    enemy.shoot_timer_ticks -= 1
                    if enemy.shoot_timer_ticks <= 0:
                        enemy.shoot_timer_ticks = enemy.shoot_interval_ticks
                        self.spawn_enemy_projectile(enemy)
                else:
                    # The EXE line-of-sight branch only calls the projectile
                    # helper when the actor is on the player's row and facing
                    # him.  Keep the timer warm but do not let off-screen /
                    # back-turned guards fire blindly every period.
                    enemy.shoot_timer_ticks = min(enemy.shoot_timer_ticks + 1, enemy.shoot_interval_ticks)

        self.update_barrels_tick()
        self.update_projectiles_tick()

        kept_explosions: list[Explosion] = []
        for explosion in self.entities.explosions:
            explosion.frame_counter += 1
            explosion.ticks_left -= 1
            if explosion.ticks_left > 0:
                kept_explosions.append(explosion)
        self.entities.explosions = kept_explosions

        kept_popups: list[ScorePopup] = []
        for popup in self.entities.score_popups:
            popup.ticks_left -= 1
            popup.y -= 1
            if popup.ticks_left > 0:
                kept_popups.append(popup)
        self.entities.score_popups = kept_popups

    def move_axis_pixels(self, dx: int | float, dy: int | float) -> bool:
        """Move pixel-by-pixel for reconstructed dynamic overlap interactions."""
        p = self.player
        if not self.collision_enabled:
            p.x += dx
            p.y += dy
            p.grounded = False
            return False
        blocked = False
        if dx:
            step = 1 if dx > 0 else -1
            for _ in range(abs(int(dx))):
                p.x += step
                barrel = self.player_touching_barrel()
                if barrel is not None:
                    if self.try_push_barrel(barrel, step):
                        pass
                    else:
                        # EXE state 0x1388/0x1389 handles the barrel/player
                        # overlap as a transient actor interaction instead of a
                        # hard tile collision.  When pushed into a wall the
                        # barrel is turned/nudged away and the player is allowed
                        # to pass through its cell until the overlap resolves.
                        self.release_barrel_against_wall(barrel, step)
                if self.player_collides():
                    p.x -= step
                    blocked = True
                    self._ignore_barrel_collision = None
                    break
                if self._ignore_barrel_collision is not None and not self.player_overlaps_barrel(self._ignore_barrel_collision):
                    self._ignore_barrel_collision = None
                    self._ignore_barrel_collision_ticks = 0
        if dy:
            step = 1 if dy > 0 else -1
            for _ in range(abs(int(dy))):
                prev_bottom = p.y + PLAYER_COLLISION_BOTTOM
                p.y += step
                if step < 0:
                    if self.player_collides():
                        p.y -= step
                        blocked = True
                        break
                    p.grounded = False
                else:
                    new_bottom = p.y + PLAYER_COLLISION_BOTTOM
                    landing_y = self.player_landing_y(prev_bottom, new_bottom)
                    if landing_y is not None:
                        p.y = landing_y
                        p.grounded = True
                        p.jump_anim_timer = 0
                        blocked = True
                        break
                    p.grounded = False
        return blocked

    def move_player_horizontal_tick(self, step: int) -> bool:
        """Apply one atomic SAM1:0xB7D9 horizontal destination probe."""
        p = self.player
        if not self.collision_enabled:
            p.x += step
            p.grounded = False
            return False
        old_x = p.x
        p.x += step
        barrel = self.player_touching_barrel()
        if barrel is not None:
            # Raw 0xA7 is handled by its actor overlap branch, not as a static
            # runtime-grid cell. Keep the reconstructed per-pixel push path for
            # that special case while normal map collision stays atomic.
            p.x = old_x
            return self.move_axis_pixels(step, 0)
        if self.player_collides():
            p.x = old_x
            return True
        if self._ignore_barrel_collision is not None and not self.player_overlaps_barrel(self._ignore_barrel_collision):
            self._ignore_barrel_collision = None
            self._ignore_barrel_collision_ticks = 0
        return False

    def move_player_upward_tick(self, step: int) -> bool:
        """Apply the normal jump's atomic upward probe from SAM1:0xBD22..0xBD80."""
        p = self.player
        if not self.collision_enabled:
            p.y -= step
            p.grounded = False
            return False
        p.y -= step
        if self.player_collides():
            p.y += step
            return True
        p.grounded = False
        return False

    def move_player_fall_tick(self, step: int) -> bool:
        """Apply one atomic SAM1:0xB8B3 fall-table displacement."""
        p = self.player
        if not self.collision_enabled:
            p.y += step
            p.grounded = False
            return False
        prev_bottom = p.y + PLAYER_COLLISION_BOTTOM
        p.y += step
        new_bottom = p.y + PLAYER_COLLISION_BOTTOM
        # B8B3 has its own downward probes; it does not call the generic B7D9
        # four-corner overlap helper. Both body and one-way landings align Y
        # down to the containing 16-pixel row.
        if self.player_fall_static_blocked():
            p.y = float(int(p.y) & ~0x0F)
            p.grounded = True
            p.jump_anim_timer = 0
            return True
        landing_y = self.dynamic_player_landing_y(prev_bottom, new_bottom)
        if landing_y is not None:
            p.y = landing_y
            p.grounded = True
            p.jump_anim_timer = 0
            return True
        if self.player_dynamic_body_collides():
            # Dynamic solid actors do not live in the reconstructed runtime
            # grid. Keep their overlap resolution separate from the exact
            # static B8B3 probes until their actor/player branches are isolated.
            p.y = float(int(p.y) & ~0x0F)
            p.grounded = True
            p.jump_anim_timer = 0
            return True
        p.grounded = False
        return False

    def move_axis(self, dx: float, dy: float) -> None:
        # Compatibility wrapper for older callers.  Mission player movement now
        # uses move_axis_pixels() so collision is checked one DOS pixel at a time.
        self.move_axis_pixels(dx, dy)


    def update_player_anim_state(self, *, moving: bool) -> None:
        p = self.player
        if p.fire_held and p.fire_pose_active:
            p.anim_state = PLAYER_STATE_FIRE_LEFT if p.facing < 0 else PLAYER_STATE_FIRE_RIGHT
            return
        # The ordinary DS:6EC1 jump uses directional 0x0D/0x0E air poses.
        # Alternating 0x0F/0x10 belongs to the distinct DS:69F5/69F6 path.
        # Falling from an edge keeps the normal facing/idle/walk state.
        if p.jump_anim_timer > 0:
            p.anim_state = PLAYER_STATE_AIR_LEFT if p.facing < 0 else PLAYER_STATE_AIR_RIGHT
            return
        if moving:
            p.anim_state = PLAYER_STATE_WALK_LEFT if p.facing < 0 else PLAYER_STATE_WALK_RIGHT
        else:
            p.anim_state = PLAYER_STATE_IDLE_LEFT if p.facing < 0 else PLAYER_STATE_IDLE_RIGHT

    def player_landing_y(self, prev_bottom: float, new_bottom: float) -> float | None:
        p = self.player
        candidates: list[float] = []
        for sample_x in (int(p.x + 3), int(p.x + 12)):
            tile_x = sample_x // TILE
            tile_y = int(new_bottom) // TILE
            if self.cell_blocks_floor(tile_x, tile_y, prev_bottom=prev_bottom, new_bottom=new_bottom):
                candidates.append(float(tile_y * TILE - PLAYER_COLLISION_BOTTOM - 1))
        platform_y = self.platform_landing_y(prev_bottom, new_bottom)
        if platform_y is not None:
            candidates.append(platform_y)
        barrel_y = self.player_barrel_landing_y(prev_bottom, new_bottom)
        if barrel_y is not None:
            candidates.append(barrel_y)
        return min(candidates) if candidates else None

    def player_fall_static_blocked(self) -> bool:
        """Mirror the static runtime-grid probes in SAM1:0xB902..0xBA30."""
        p = self.player
        sample_xs = (int(p.x + 3) // TILE, int(p.x + 12) // TILE)
        body_y = int(p.y + 16) // TILE
        if any(self.cell_blocks_body(tile_x, body_y) for tile_x in sample_xs):
            return True
        # B94D skips the +0x1CD one-way path for the shallow part of the fall.
        if p.fall_ticks <= 0x0A:
            return False
        foot_y = int(p.y + 16) // TILE
        if not any(self.cell_blocks_foot(tile_x, foot_y) for tile_x in sample_xs):
            return False
        # B9D6..BA30 rejects a platform cell that is already present around
        # y+7. This is what limits +0x1CD to crossing a top surface.
        upper_y = int(p.y + 7) // TILE
        return not any(self.cell_blocks_foot(tile_x, upper_y) for tile_x in sample_xs)

    def dynamic_player_landing_y(self, prev_bottom: float, new_bottom: float) -> float | None:
        """Return a crossed moving-actor top without applying static-grid rules."""
        candidates = [
            landing_y
            for landing_y in (
                self.platform_landing_y(prev_bottom, new_bottom),
                self.player_barrel_landing_y(prev_bottom, new_bottom),
            )
            if landing_y is not None
        ]
        return min(candidates) if candidates else None

    def player_collides(self) -> bool:
        p = self.player
        for probe in player_body_probes(p.x, p.y):
            if self.cell_blocks_body(probe.tile_x, probe.tile_y):
                return True
        return self.player_dynamic_body_collides()

    def player_dynamic_body_collides(self) -> bool:
        """Probe actor-backed solids that are absent from the static grid."""
        p = self.player
        for probe in player_body_probes(p.x, p.y):
            probe_x = probe.tile_x * TILE + (probe.pixel_x % TILE)
            probe_y = probe.tile_y * TILE + (probe.pixel_y % TILE)
            for enemy in self.entities.enemies:
                if self.actor_is_indestructible_solid(enemy) and self.actor_contains_point(enemy, probe_x, probe_y):
                    return True
            for barrel in self.entities.barrels:
                if barrel is self._ignore_barrel_collision and self._ignore_barrel_collision_ticks > 0:
                    continue
                if barrel.x <= probe_x <= barrel.x + TILE - 1 and barrel.y <= probe_y <= barrel.y + TILE - 1:
                    return True
        return False

    def player_floor_blocked(self, prev_bottom: float, new_bottom: float) -> bool:
        p = self.player
        foot_y = int(new_bottom)
        left = int(p.x + 3) // TILE
        right = int(p.x + 12) // TILE
        tile_y = foot_y // TILE
        return (
            self.cell_blocks_floor(left, tile_y, prev_bottom=prev_bottom, new_bottom=new_bottom)
            or self.cell_blocks_floor(right, tile_y, prev_bottom=prev_bottom, new_bottom=new_bottom)
        )

    def cell_solid(self, x: int, y: int) -> bool:
        return self.cell_blocks_body(x, y)

    def removed_runtime_source_keys(self) -> set[tuple[int, int, int, str]]:
        # Runtime actors are extracted from raw map tokens and simulated from
        # actor slots.  Their source tokens must not stay in the reconstructed
        # runtime collision grid, otherwise enemy projectiles can immediately
        # collide with their own map marker and some actors behave as invisible
        # static walls.
        removed = set(self.dynamic_source_keys()) | set(self.collected_cells) | set(self.opened_doors) | set(self.opened_exit_doors)
        if self.laser_field_deactivated:
            removed |= self.laser_field_source_keys()
        return removed

    def dynamic_source_keys(self) -> set[tuple[int, int, int, str]]:
        if self.is_world_map:
            return set()
        if self._dynamic_source_keys_cache is None:
            info = self.episode.levels[self.level_index]
            self._dynamic_source_keys_cache = {
                self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
                for cell in iter_map_cells(info)
                if is_dynamic_mission_code(cell.code)
            }
        return set(self._dynamic_source_keys_cache)

    def laser_field_visible(self) -> bool:
        # Runtime cA 0x025B is one of the EXE's globally blink-redrawn cells.
        # The exact timer is tied to DS:6840 redraw toggles; 4 DOS ticks gives
        # a close visual cadence in this runtime.
        return (self.anim_ticks // 4) % 2 == 0

    def laser_field_source_keys(self) -> set[tuple[int, int, int, str]]:
        if self.is_world_map:
            return set()
        if self._laser_field_source_keys_cache is None:
            info = self.episode.levels[self.level_index]
            self._laser_field_source_keys_cache = {
                self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
                for cell in iter_map_cells(info)
                if cell.code == LASER_FIELD_CODE
            }
        return set(self._laser_field_source_keys_cache)

    def runtime_collision_grid(self):
        info = self.episode.levels[self.level_index]
        removed = frozenset(self.removed_runtime_source_keys())
        overrides = {HIDDEN_PLATFORM_CODE: ACTIVE_HIDDEN_PLATFORM_COLLISION_CODE} if self.has_glasses else {}
        cache_key = (self.level_index, removed, tuple(sorted(overrides.items())))
        if self._collision_grid_cache_key != cache_key:
            self._collision_grid_cache = build_runtime_collision_grid(info, removed_source_keys=set(removed), code_collision_overrides=overrides)
            self._collision_grid_cache_key = cache_key
        return self._collision_grid_cache

    def runtime_collision_cell(self, x: int, y: int):
        return self.runtime_collision_grid().get((x, y))

    def cell_blocks_body(self, x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
            return True
        if any(ox == x and oy - 1 == y for ox, oy, _code, _layer in self.opened_exit_doors):
            # State 0x16 clears collision for the upper cell too: the lower
            # 0x027D becomes 0x027E, and the upper 0x0279 cell is moved to
            # layer-B visual 0x027A with +0x1CC cleared.
            return False
        cell = self.runtime_collision_cell(x, y)
        if cell is None:
            return False
        if is_door_code(cell.source_code):
            return door_unlocked_by(cell.source_code) not in self.owned_keys
        if is_exit_door_code(cell.source_code):
            # The raw source is removed from the runtime grid only once the
            # 0x027B/state-0x16 blast completes.  Until then it remains solid.
            return True
        return cell.body_solid

    def cell_blocks_floor(self, x: int, y: int, *, prev_bottom: float, new_bottom: float) -> bool:
        if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
            return True
        if any(ox == x and oy - 1 == y for ox, oy, _code, _layer in self.opened_exit_doors):
            return False
        cell = self.runtime_collision_cell(x, y)
        if cell is None:
            return False
        if is_door_code(cell.source_code):
            return door_unlocked_by(cell.source_code) not in self.owned_keys
        if is_exit_door_code(cell.source_code):
            return True
        if cell.body_solid:
            return True
        if cell.foot_solid:
            tile_top = y * TILE
            return prev_bottom <= tile_top + 1 and new_bottom >= tile_top
        return False

    def cell_blocks_foot(self, x: int, y: int) -> bool:
        """Read runtime byte +0x1CD without broadening it into body solidity."""
        if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
            return True
        if any(ox == x and oy - 1 == y for ox, oy, _code, _layer in self.opened_exit_doors):
            return False
        cell = self.runtime_collision_cell(x, y)
        return bool(cell and cell.foot_solid)

    def runtime_cell_key(self, x: int, y: int, code: int, layer: str) -> tuple[int, int, int, str]:
        return (x, y, code, layer)


    def enemy_collides(self, enemy) -> bool:
        l, t, r, b = self.actor_rect(enemy)
        left = int(l) // TILE
        right = int(r) // TILE
        top = int(t) // TILE
        bottom = int(b) // TILE
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                if self.cell_blocks_body(x, y):
                    return True
        return False

    def enemy_has_floor_ahead(self, enemy) -> bool:
        left, _top, right, bottom = self.actor_rect(enemy)
        foot_x = int((right + 1) if enemy.direction > 0 else (left - 1)) // TILE
        foot_y = int(bottom + 1) // TILE
        if foot_x < 0 or foot_x >= LEVEL_W or foot_y < 0 or foot_y >= LEVEL_H:
            return False
        cell = self.runtime_collision_cell(foot_x, foot_y)
        return bool(cell and (cell.body_solid or cell.foot_solid))


    def enemy_has_ceiling_track(self, enemy) -> bool:
        # State 0x21 uses the EXE collision table around the candidate actor
        # position.  A practical equivalent is: the tile directly above the
        # crawler's centre/leading half must still be solid after the move.
        # Checking the candidate centre prevents the crawler from travelling
        # beyond the visible support block above it.
        probe_y = int(enemy.y - 1) // TILE
        if probe_y < 0:
            return False
        probe_x = int(enemy.x + TILE / 2 + enemy.direction * (TILE / 2 - 1)) // TILE
        if probe_x < 0 or probe_x >= LEVEL_W:
            return False
        cell = self.runtime_collision_cell(probe_x, probe_y)
        return bool(cell and (cell.body_solid or cell.foot_solid))

    def enemy_has_ceiling_ahead(self, enemy) -> bool:
        # Backwards-compatible wrapper for older notes/tools.
        return self.enemy_has_ceiling_track(enemy)

    def platform_collides(self, platform: MovingPlatform) -> bool:
        left = int(platform.x) // TILE
        right = int(platform.x + TILE - 1) // TILE
        top = int(platform.y) // TILE
        bottom = int(platform.y + TILE - 1) // TILE
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                if self.cell_solid(x, y):
                    return True
        return False

    def update_barrels_tick(self) -> None:
        for barrel in self.entities.barrels:
            carry_player = self.barrel_below() is barrel and self.player.grounded
            landing_y = self.barrel_landing_y(barrel, barrel.y + TILE, barrel.y + TILE + 1)
            if landing_y is not None and landing_y >= barrel.y and abs(barrel.y - landing_y) <= 1.0:
                barrel.y = landing_y
                barrel.grounded = True
                barrel.fall_ticks = 0
                continue
            barrel.grounded = False
            barrel.fall_ticks = min(FALL_COUNTER_MAX, barrel.fall_ticks + 1)
            fall_step = PLAYER_VERTICAL_STEP_TABLE[barrel.fall_ticks]
            moved = self.move_barrel_vertical(barrel, fall_step)
            if carry_player and moved:
                self.player.y += moved
                self.player.grounded = True

    def move_barrel_vertical(self, barrel: PushableBarrel, dy: int) -> int:
        moved = 0
        for _ in range(max(0, int(dy))):
            prev_bottom = barrel.y + TILE
            new_bottom = prev_bottom + 1
            landing_y = self.barrel_landing_y(barrel, prev_bottom, new_bottom)
            if landing_y is not None and landing_y >= barrel.y:
                barrel.y = landing_y
                barrel.grounded = True
                barrel.fall_ticks = 0
                return moved
            old_y = barrel.y
            barrel.y += 1
            if self.barrel_collides(barrel):
                barrel.y = old_y
                barrel.grounded = True
                barrel.fall_ticks = 0
                return moved
            moved += 1
        return moved

    def barrel_landing_y(self, barrel: PushableBarrel, prev_bottom: float, new_bottom: float) -> float | None:
        candidates: list[float] = []
        for sample_x in (int(barrel.x + 3), int(barrel.x + 12)):
            tile_x = sample_x // TILE
            tile_y = int(new_bottom) // TILE
            if self.cell_blocks_floor(tile_x, tile_y, prev_bottom=prev_bottom, new_bottom=new_bottom):
                candidates.append(float(tile_y * TILE - TILE))
        for other in self.entities.barrels:
            if other is barrel:
                continue
            horizontal = barrel.x + TILE - 1 >= other.x + 2 and barrel.x <= other.x + TILE - 3
            vertical = other.y <= new_bottom <= other.y + 4 and prev_bottom <= other.y + 1
            if horizontal and vertical:
                candidates.append(float(other.y - TILE))
        return min(candidates) if candidates else None

    def platform_below(self) -> MovingPlatform | None:
        p = self.player
        player_left = p.x
        player_right = p.x + PLAYER_W - 1
        player_bottom = p.y + PLAYER_H
        for platform in self.entities.platforms:
            horizontal = player_right >= platform.x + 2 and player_left <= platform.x + TILE - 3
            vertical = platform.y <= player_bottom <= platform.y + 4
            if horizontal and vertical:
                return platform
        return None

    def platform_landing_y(self, prev_bottom: float, new_bottom: float) -> float | None:
        """Return the topmost moving-platform landing crossed this player tick."""
        p = self.player
        player_left = p.x
        player_right = p.x + PLAYER_W - 1
        # Player map probes use the inclusive collision pixel at y+15. Dynamic
        # platform tops line up with the sprite base at y+16, so shift both
        # endpoints before applying the one-way downward crossing test.
        prev_base = prev_bottom + 1
        new_base = new_bottom + 1
        candidates: list[float] = []
        for platform in self.entities.platforms:
            horizontal = player_right >= platform.x + 2 and player_left <= platform.x + TILE - 3
            vertical = prev_base <= platform.y <= new_base
            if horizontal and vertical:
                candidates.append(float(platform.y - PLAYER_H))
        return min(candidates) if candidates else None

    def update_barrel_overlap_state(self) -> None:
        """Expire the transient pass-through state used for pushable barrels."""
        barrel = self._ignore_barrel_collision
        if barrel is None:
            return
        if not self.player_overlaps_barrel(barrel):
            self._ignore_barrel_collision = None
            self._ignore_barrel_collision_ticks = 0
            return
        self._ignore_barrel_collision_ticks = max(0, self._ignore_barrel_collision_ticks - 1)
        if self._ignore_barrel_collision_ticks == 0:
            # Do not re-enable collision while still deeply overlapped; that is
            # what made the port look as if the barrel stuck to the player.
            self._ignore_barrel_collision_ticks = 1

    def player_overlaps_barrel(self, barrel: PushableBarrel) -> bool:
        p = self.player
        return (
            p.x + PLAYER_W - 1 >= barrel.x
            and p.x <= barrel.x + TILE - 1
            and p.y + PLAYER_H - 1 >= barrel.y
            and p.y <= barrel.y + TILE - 1
        )

    def release_barrel_against_wall(self, barrel: PushableBarrel, push_step: int) -> None:
        """Match the EXE-style anti-stick branch for bank6 tile 24 barrels.

        The disassembly around SAM1:0x83c4..0x848a checks the player's
        shrunken overlap against object id 0x00A7 and then transitions the
        actor instead of treating it as an ordinary solid tile.  For the Python
        runtime that means: turn the barrel away from the wall, try to nudge it
        out of the blocking cell, and temporarily ignore its body collision for
        the player until the overlap clears.
        """
        barrel.direction = -push_step
        for _ in range(4):
            if self.try_push_barrel(barrel, -push_step):
                break
        self._ignore_barrel_collision = barrel
        self._ignore_barrel_collision_ticks = 12

    def barrel_below(self) -> PushableBarrel | None:
        p = self.player
        player_left = p.x
        player_right = p.x + PLAYER_W - 1
        player_bottom = p.y + PLAYER_H
        for barrel in self.entities.barrels:
            horizontal = player_right >= barrel.x + 2 and player_left <= barrel.x + TILE - 3
            vertical = barrel.y <= player_bottom <= barrel.y + 4
            if horizontal and vertical:
                return barrel
        return None

    def player_barrel_landing_y(self, prev_bottom: float, new_bottom: float) -> float | None:
        """Return the topmost barrel surface crossed by the falling player."""
        p = self.player
        player_left = p.x
        player_right = p.x + PLAYER_W - 1
        prev_base = prev_bottom + 1
        new_base = new_bottom + 1
        candidates: list[float] = []
        for barrel in self.entities.barrels:
            horizontal = player_right >= barrel.x + 2 and player_left <= barrel.x + TILE - 3
            vertical = prev_base <= barrel.y <= new_base
            if horizontal and vertical:
                candidates.append(float(barrel.y - PLAYER_H))
        return min(candidates) if candidates else None

    def player_touching_barrel(self) -> PushableBarrel | None:
        p = self.player
        for barrel in self.entities.barrels:
            if self.player_overlaps_barrel(barrel):
                return barrel
        return None

    def barrel_collides(self, barrel: PushableBarrel) -> bool:
        left = int(barrel.x) // TILE
        right = int(barrel.x + TILE - 1) // TILE
        top = int(barrel.y) // TILE
        bottom = int(barrel.y + TILE - 1) // TILE
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                if self.cell_solid(x, y):
                    return True
        for other in self.entities.barrels:
            if other is barrel:
                continue
            if barrel.x + TILE - 1 >= other.x and barrel.x <= other.x + TILE - 1 and barrel.y + TILE - 1 >= other.y and barrel.y <= other.y + TILE - 1:
                return True
        return False

    def try_push_barrel(self, barrel: PushableBarrel, step: int) -> bool:
        old_x = barrel.x
        barrel.x += step
        if self.barrel_collides(barrel):
            barrel.x = old_x
            return False
        barrel.direction = step
        return True

    def player_on_platform(self) -> bool:
        return self.platform_below() is not None or self.barrel_below() is not None

    def update_player_interactions(self, dt: float) -> None:
        self.check_teleporter_touch()
        self.collect_touching_codes()
        self.check_exit_door_touch()
        self.collect_rip_enemies()
        self.check_laser_field_touch()
        self.check_spike_touch()
        self.check_beam_touch()
        self.check_enemy_touch(dt)

    def player_overlapping_cells(self):
        p = self.player
        left = int(p.x) // TILE
        right = int(p.x + PLAYER_W - 1) // TILE
        top = int(p.y) // TILE
        bottom = int(p.y + PLAYER_H - 1) // TILE
        info = self.episode.levels[self.level_index]
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                yield from cells_at(info, x, y)

    def collect_touching_codes(self) -> None:
        changed = False
        for cell in self.player_overlapping_cells():
            key = self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
            if key in self.collected_cells or key in self.opened_doors or key in self.opened_exit_doors:
                continue
            kind = mission_code_kind(cell.code)
            if is_collectible_code(cell.code):
                self.collected_cells.add(key)
                changed = True
                if kind == "key":
                    self.owned_keys.add(cell.code)
                    self.play_sound(SOUND_PICKUP)
                elif kind == "ammo":
                    # Runtime visual 0x012D branch at SAM1:0xC0BF..0xC106
                    # adds five shots, clamps DS:6858 to 0x63, clears the
                    # map cell and plays sound 0x05.
                    self.ammo = min(MAX_AMMO, self.ammo + 5)
                    self.play_sound(SOUND_PICKUP)
                elif kind == "dynamite":
                    # Runtime visual 0x027B branch at SAM1:0xCB72..0xCBE5:
                    # set DS:69F4, clear the cell, play sound 0x05, award 500
                    # points and spawn the 500 popup.  DS:69F4 is later tested
                    # by the level-exit door visual 0x027D.
                    self.has_dynamite = True
                    self.score += 500
                    self.play_sound(SOUND_PICKUP)
                    self.spawn_score_popup(cell.x * TILE, cell.y * TILE, 500)
                elif (score_value := score_value_for_code(cell.code)) is not None:
                    self.score += score_value
                    if cell.code == FLOPPY_DISK_CODE:
                        self.has_floppy_disk = True
                    self.play_sound(SOUND_SCORE_1000 if score_value >= 1000 else SOUND_PICKUP)
                    popup_tile = score_popup_tile_for_value(score_value)
                    if popup_tile is not None:
                        self.entities.score_popups.append(
                            ScorePopup(float(cell.x * TILE), float(cell.y * TILE - 8), score_value, popup_tile)
                        )
                elif kind == "glasses":
                    self.has_glasses = True
                    self.play_sound(SOUND_PICKUP)
            elif cell.code == LASER_COMPUTER_CODE and not self.laser_field_deactivated:
                if self.has_floppy_disk:
                    self.deactivate_laser_field()
                    changed = True
                else:
                    if self._laser_computer_last_warn_key != key:
                        self.play_sound(SOUND_NO_AMMO)
                        self._laser_computer_last_warn_key = key
            elif is_door_code(cell.code) and door_unlocked_by(cell.code) in self.owned_keys:
                self.opened_doors.add(key)
                self.owned_keys.discard(door_unlocked_by(cell.code))
                self.play_sound(SOUND_SCORE_1000)
                changed = True
        if changed:
            self.rebuild_level_image()

    def exit_door_source_key(self, cell) -> tuple[int, int, int, str]:
        return self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)

    def update_exit_door_blasts(self) -> None:
        if not self.exit_door_blast_timers:
            return
        completed: list[tuple[int, int, int, str]] = []
        for key in list(self.exit_door_blast_timers):
            self.exit_door_blast_timers[key] -= 1
            if self.exit_door_blast_timers[key] <= 0:
                completed.append(key)
        if not completed:
            return
        info = self.episode.levels[self.level_index]
        for key in completed:
            self.exit_door_blast_timers.pop(key, None)
            self.opened_exit_doors.add(key)
            x, y, code, layer = key
            # State 0x16 does not erase the exit door.  At SAM1:0x7490..0x7523
            # it rewrites the lower 0x027D cell to 0x027E and rewrites the
            # upper 0x0279 cell into layer-B visual 0x027A; both cells clear
            # +0x1CC for passability.  The renderer overlays the two broken
            # door tiles instead of deleting the raw 0x71 footprint.
            self.spawn_projectile_explosion(x * TILE + TILE / 2, y * TILE + TILE / 2)
            self.spawn_projectile_explosion(x * TILE + TILE / 2, (y - 1) * TILE + TILE / 2)
        self.rebuild_level_image()

    def check_exit_door_touch(self) -> None:
        if self.is_world_map or self.player_dead_timer > 0:
            return
        for cell in self.player_overlapping_cells():
            if not is_exit_door_code(cell.code):
                continue
            key = self.exit_door_source_key(cell)
            if key in self.opened_exit_doors:
                self.complete_level_from_exit()
                return
            if key in self.exit_door_blast_timers:
                return
            if not self.has_dynamite:
                # SAM1:0xCD73 path shows the "need dynamite" text once via
                # DS:69EE; keep this non-destructive and quiet until the text
                # renderer is rebuilt.
                return
            # SAM1:0xCBFA..0xCD71: consume DS:69F4, play sound 0x0B, spawn
            # object 0x027B/state 0x16 with DS:34D8=0x28.  Do not remove the
            # source immediately; the door remains blocking while it blows.
            self.has_dynamite = False
            self.exit_door_blast_timers[key] = 0x28
            self.play_sound(SOUND_EXIT_DYNAMITE)
            self.spawn_projectile_explosion(cell.x * TILE + TILE / 2, cell.y * TILE + TILE / 2)
            return

    def complete_level_from_exit(self) -> None:
        # The true exit branch around SAM1:0xCDF4 continues into a mission-end
        # transition/menu flow.  For the playable port, returning to the
        # overworld is the closest state transition already implemented.
        if self.level_exit_pending:
            return
        self.level_exit_pending = True
        self.last_world_position = self.last_world_position or self.find_world_spawn()
        self.level_index = 0
        self.load_level(reset_player=True)

    def deactivate_laser_field(self) -> None:
        if self.laser_field_deactivated:
            return
        # SAM1:0xD25F clears DS:69EC, sets DS:69ED, then scans the whole
        # runtime grid and zeroes every cA == 0x025B cell.  Raw map code 0x82
        # is the source byte that generates cA 0x025B.
        self.has_floppy_disk = False
        self.laser_field_deactivated = True
        self._laser_computer_last_warn_key = None
        self.collected_cells |= self.laser_field_source_keys()
        self.play_sound(0x18)

    def check_laser_field_touch(self) -> None:
        if self.hurt_flash > 0 or self.laser_field_deactivated or not self.laser_field_visible():
            return
        p = self.player
        left, top = p.x, p.y
        right, bottom = p.x + PLAYER_W - 1, p.y + PLAYER_H - 1
        for cell in self.player_overlapping_cells():
            if cell.code != LASER_FIELD_CODE:
                continue
            key = self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
            if key in self.collected_cells:
                continue
            lx1 = cell.x * TILE + 2
            ly1 = cell.y * TILE + 2
            lx2 = cell.x * TILE + TILE - 3
            ly2 = cell.y * TILE + TILE - 3
            if right < lx1 or left > lx2 or bottom < ly1 or top > ly2:
                continue
            self.kill_player()
            return

    def collect_rip_enemies(self) -> None:
        p = self.player
        left, top = p.x, p.y
        right, bottom = p.x + PLAYER_W - 1, p.y + PLAYER_H - 1
        kept = []
        for enemy in self.entities.enemies:
            if enemy.is_rip and not (right < enemy.x or left > enemy.x + TILE - 1 or bottom < enemy.y or top > enemy.y + TILE - 1):
                self.score += BANK14_RIP_PICKUP_SCORE
                self.spawn_score_popup(enemy.x, enemy.y, BANK14_RIP_PICKUP_SCORE)
                self.play_sound(SOUND_PICKUP)
                continue
            kept.append(enemy)
        self.entities.enemies = kept


    def check_spike_touch(self) -> None:
        if self.hurt_flash > 0:
            return
        p = self.player
        left, top = p.x, p.y
        right, bottom = p.x + PLAYER_W - 1, p.y + PLAYER_H - 1
        for spike in self.entities.spike_traps:
            if not spike_is_dangerous(spike.timer_ticks):
                continue
            sx = spike.x
            sy = spike.draw_y
            if right < sx + 2 or left > sx + TILE - 3:
                continue
            if bottom < sy + 2 or top > sy + TILE - 3:
                continue
            self.hurt_player()
            break

    def check_beam_touch(self) -> None:
        if self.hurt_flash > 0:
            return
        p = self.player
        left, top = p.x, p.y
        right, bottom = p.x + PLAYER_W - 1, p.y + PLAYER_H - 1
        for beam in self.entities.beam_traps:
            if not beam_is_dangerous(beam.timer_ticks):
                continue
            phase = beam_phase_for_timer(beam.timer_ticks)
            if phase is None:
                continue
            rects = self.beam_trap_rects(beam, phase)
            for bx1, by1, bx2, by2 in rects:
                if right < bx1 or left > bx2 or bottom < by1 or top > by2:
                    continue
                self.hurt_player()
                return

    def beam_trap_rects(self, beam: BeamTrap, phase: int) -> list[tuple[float, float, float, float]]:
        # Damage uses the visible extended bank-3 cels.  The EXE drives object
        # ids 0x01AD+/0x01B5+ while state 0x0F/0x10 is active.
        if beam.kind == "vertical":
            cells = [(0, 0)]
            if phase >= 1:
                cells.append((0, -1))
            if phase >= 2:
                cells.append((0, -2))
        else:
            cells = [(0, 0)]
            if phase >= 1:
                cells.append((-1, 0))
            if phase >= 2:
                cells.append((-2, 0))
        return [
            (beam.x + dx * TILE + 2, beam.y + dy * TILE + 2, beam.x + dx * TILE + TILE - 3, beam.y + dy * TILE + TILE - 3)
            for dx, dy in cells
        ]

    def check_enemy_touch(self, dt: float) -> None:
        if self.hurt_flash > 0:
            self.hurt_flash = max(0.0, self.hurt_flash - dt)
            return
        p = self.player
        left, top = p.x, p.y
        right, bottom = p.x + PLAYER_W - 1, p.y + PLAYER_H - 1
        for enemy in self.entities.enemies:
            if enemy.is_rip:
                continue
            if right < enemy.x or left > enemy.x + TILE - 1:
                continue
            if bottom < enemy.y or top > enemy.y + TILE - 1:
                continue
            # Generic enemy body contact routes through the hurt helper, not
            # the hard-death tile dispatcher.  It removes one life and starts
            # the 0x1E-tick invulnerability window.
            self.hurt_player()
            break

    def current_world_level_hint(self) -> str:
        if not self.is_world_map:
            return ""
        p = self.player
        center_x = p.x + PLAYER_W / 2
        center_y = p.y + PLAYER_H / 2
        for x, y, level in self.world_entrances():
            dist = abs(center_x - (x * TILE + TILE / 2)) + abs(center_y - (y * TILE + TILE / 2))
            if dist <= 20:
                return f"   Enter: level {level}"
        return ""

    def camera(self) -> tuple[int, int]:
        p = self.player
        view_w, screen_h = self.viewport_size()
        view_h = max(1, screen_h - STATUS_BAR_H)
        max_x = max(0, LEVEL_W * TILE - view_w)
        max_y = max(0, LEVEL_H * TILE - view_h)
        x = int(min(max(p.x + PLAYER_W / 2 - view_w / 2, 0), max_x))
        y = int(min(max(p.y + PLAYER_H / 2 - view_h / 2, 0), max_y))
        return x, y

    def draw(self) -> None:
        current_phase = self.current_tile_anim_tick()
        if self.level_image is None or (not self.is_world_map and self._level_image_phase != current_phase):
            self.render_level_image_for_phase(current_phase)
        if self.level_image is None:
            return
        cam_x, cam_y = self.camera()
        view_w, screen_h = self.viewport_size()
        world_h = max(1, screen_h - STATUS_BAR_H)
        world_frame = self.level_image.crop((cam_x, cam_y, cam_x + view_w, cam_y + world_h)).convert("RGBA")
        frame = Image.new("RGBA", (view_w, screen_h), (0, 0, 0, 255))
        frame.alpha_composite(world_frame, (0, 0))
        draw = ImageDraw.Draw(frame)

        p = self.player
        px = int(p.x - cam_x)
        py = int(p.y - cam_y)
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
            self.draw_entities(frame, cam_x, cam_y)

        self.draw_status_bar(frame, view_w, screen_h)

        scaled_frame = frame.resize((view_w * self.zoom, screen_h * self.zoom), Image.Resampling.NEAREST) if self.zoom != 1 else frame
        out_w = max(self.canvas_w, scaled_frame.width)
        out_h = max(self.canvas_h, scaled_frame.height)
        out = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 255))
        out.alpha_composite(scaled_frame, (0, 0))

        self.frame_photo = ImageTk.PhotoImage(out)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.frame_photo, anchor="nw")

    def draw_world_player(self, frame: Image.Image, px: int, py: int) -> None:
        self.draw_player_sprite(frame, px, py, offset=(-2, -1))

    def draw_player_sprite(self, frame: Image.Image, px: int, py: int, *, offset: tuple[int, int] = (0, 0)) -> None:
        if self.is_world_map:
            tile_ref = (13, 0)
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
            self.draw_code_sprite(frame, platform.code, int(platform.x - cam_x), int(platform.y - cam_y))
        for barrel in self.entities.barrels:
            self.draw_code_sprite(frame, barrel.code, int(barrel.x - cam_x), int(barrel.y - cam_y))
        for satellite in self.entities.satellites:
            tile = self.episode.tiles16.get(*satellite_tile(satellite.frame_index))
            if tile:
                frame.alpha_composite(tile, (int(satellite.x - cam_x), int(satellite.y - cam_y)))
        for enemy in self.entities.enemies:
            if enemy.code == 0x24:
                multi_refs = state27_actor_refs(
                    enemy.direction,
                    enemy.frame_counter,
                    walking_phase=(enemy.kind == "state27_shooter" and enemy.phase_ticks > 0),
                )
            else:
                multi_refs = multi_tile_actor_refs(enemy.code, enemy.direction, enemy.frame_counter)
            if multi_refs is not None:
                for relx, rely, bank, tile_no in multi_refs:
                    tile = self.episode.tiles16.get(bank, tile_no)
                    if tile:
                        if enemy.code in {0xAE, 0x24, 0x56, 0x58, 0x63} and enemy.direction < 0:
                            tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                        tile = self.apply_enemy_hit_flash(tile, enemy)
                        frame.alpha_composite(tile, (int(enemy.x - cam_x + relx * TILE), int(enemy.y - cam_y + rely * TILE)))
                continue
            if enemy.bank == 14 and enemy.base_tile is not None:
                animated = bank14_guard_tile(enemy.base_tile, direction=enemy.direction, frame_counter=enemy.frame_counter)
            else:
                animated = walker_tile(enemy.code, direction=enemy.direction, anim_time=enemy.anim_time, frame_counter=enemy.frame_counter)
            if enemy.kind == "state2b_anim":
                tile = self.episode.tiles16.get(*state2b_tile(enemy.frame_counter))
                if tile:
                    tile = self.apply_enemy_hit_flash(tile, enemy)
                    frame.alpha_composite(tile, (int(enemy.x - cam_x), int(enemy.y - cam_y)))
                    continue
            if enemy.kind == "state2c_anim":
                tile = self.episode.tiles16.get(*state2c_tile(enemy.code, enemy.frame_counter))
                if tile:
                    tile = self.apply_enemy_hit_flash(tile, enemy)
                    frame.alpha_composite(tile, (int(enemy.x - cam_x), int(enemy.y - cam_y)))
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
                    frame.alpha_composite(tile, (int(enemy.x - cam_x), int(enemy.y - cam_y)))
                    continue
            self.draw_code_sprite(frame, enemy.code, int(enemy.x - cam_x), int(enemy.y - cam_y))
        for spike in self.entities.spike_traps:
            tile_ref = spike_frame_for_timer(spike.kind, spike.timer_ticks)
            if tile_ref is not None:
                tile = self.episode.tiles16.get(*tile_ref)
                if tile:
                    frame.alpha_composite(tile, (int(spike.x - cam_x), int(spike.draw_y - cam_y)))
        for beam in self.entities.beam_traps:
            self.draw_beam_trap(frame, beam, cam_x, cam_y)
        draw = ImageDraw.Draw(frame)
        for shot in self.entities.projectiles:
            x = int(shot.x - cam_x)
            y = int(shot.y - cam_y)
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
                frame.alpha_composite(tile, (int(explosion.x - cam_x), int(explosion.y - cam_y)))
        for popup in self.entities.score_popups:
            tile = self.episode.tiles16.get(10, popup.tile)
            if tile:
                frame.alpha_composite(tile, (int(popup.x - cam_x), int(popup.y - cam_y)))

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
                frame.alpha_composite(tile, (int(beam.x - cam_x + relx * TILE), int(beam.y - cam_y + rely * TILE)))

    def draw_code_sprite(self, frame: Image.Image, code: int, px: int, py: int) -> None:
        from secret_agent_editor.mapping import TILE_MAP

        refs = TILE_MAP.get(code, [])
        for relx, rely, bank, tile_no in refs:
            tile = self.episode.tiles16.get(bank, tile_no)
            if tile:
                frame.alpha_composite(tile, (px + relx * TILE, py + rely * TILE))



def default_source() -> Path:
    for candidate in (ROOT / "game_data", ROOT / "game_data" / "game_data.zip", ROOT / "game_data.zip"):
        if candidate.exists():
            return candidate
    return ROOT / "game_data"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the OpenAgent prototype engine.")
    parser.add_argument("source", nargs="?", type=Path, default=default_source(), help="game_data folder or ZIP")
    parser.add_argument("--episode", type=int, default=1, choices=(1, 2, 3))
    parser.add_argument("--level", type=int, default=0)
    parser.add_argument("--zoom", type=int, default=DEFAULT_ZOOM, help="initial integer zoom, default 2 for a 320x200 DOS viewport")
    args = parser.parse_args(argv)

    campaign = load_campaign(args.source)
    app = OpenAgentApp(campaign, episode=args.episode, level=args.level, zoom=args.zoom)
    app.run()
    return 0
