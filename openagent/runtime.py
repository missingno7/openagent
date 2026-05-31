from __future__ import annotations

import argparse
import time
import tkinter as tk
from pathlib import Path

from .animation import (
    PLAYER_FIRE_HOLD_SECONDS,
    PLAYER_WALK_COUNTER_MAX,
    PLAYER_WALK_COUNTER_START,
    PLAYER_WALK_COUNTER_STEP,
    actor_walk_counter_next,
    state27_walk_counter_next,
    state1f_walk_counter_next,
    state1f_walk_counter_start,
    state2a_dog_counter_next,
)
from .hud import HUDMixin
from .entities import BeamTrap, Explosion, LevelEntities, ScorePopup, extract_level_entities, PushableBarrel
from .exe_actor_mechanics import (
    deterministic_range,
    spike_is_dangerous,
    BEAM_CYCLE_TICKS,
    beam_phase_for_timer,
    beam_is_dangerous,
    SPIKE_CYCLE_TICKS,
    STATE1E_FIRE_COOLDOWN_TICKS,
    STATE2B_ANIM_PERIOD,
    STATE2C_CONTACT_HAZARD_CODE,
    STATE29_MONEY_BAG_IDLE_OBJECT_ID,
    STATE29_MONEY_BAG_FALLING_OBJECT_ID,
    STATE29_MONEY_BAG_FALL_STEP_PX,
    STATE17_LANDMINE_CODE,
    STATE17_LANDMINE_IDLE_OBJECT_ID,
    STATE17_LANDMINE_TRIGGERED_OBJECT_ID,
    STATE17_LANDMINE_DAMAGE_FRAME,
)
from .exe_runtime_collision import runtime_cell_writes_for_code
from .level_model import cells_at, iter_map_cells
from .loader import Campaign, load_campaign
from .movement_collision import MovementCollisionMixin
from .player import Player
from .player_motion import advance_death_bounce_tick, advance_fall_tick, advance_jump_tick, horizontal_step_for_hold_ticks
from .player_lifecycle import PlayerLifecycleMixin
from .combat import CombatMixin
from .overworld import OverworldMixin
from .rendering import RenderingMixin
from .teleport import TeleportMixin
from .window import WindowMixin
from .semantics import (
    BANK14_RIP_PICKUP_SCORE,
    LASER_FIELD_CODE,
    LASER_COMPUTER_CODE,
    FLOPPY_DISK_CODE,
    MISSION_PLAYER_START_CODE,
    SPEED_BONUS_CODE,
    door_unlocked_by,
    is_collectible_code,
    is_door_code,
    is_exit_door_code,
    WATER_CODE,
    HARD_DEATH_RUNTIME_VISUAL_IDS,
    mission_code_kind,
    score_popup_tile_for_value,
    score_value_for_code,
)
from .sound import (
    SOUND_EXIT_DYNAMITE,
    SOUND_JUMP,
    SOUND_NO_AMMO,
    SOUND_PICKUP,
    SOUND_SCORE_1000,
    SoundPlayer,
)

from openagent.game_assets.constants import LEVEL_H, LEVEL_W, TILE

from .game_constants import (
    DEFAULT_ZOOM,
    DOS_TICK_HZ,
    FALL_COUNTER_MAX,
    GAME_VIEW_H,
    GAME_VIEW_W,
    JUMP_ASCENT_END_COUNTER,
    MAX_AMMO,
    MAX_ZOOM,
    MIN_ZOOM,
    PLAYER_H,
    PLAYER_VERTICAL_COUNTER_INITIAL,
    PLAYER_W,
    PLAYER_SPEED_BONUS_STEP,
    PLAYER_SPEED_BONUS_TOTAL_TICKS,
    STARTING_AMMO,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class OpenAgentApp(HUDMixin, PlayerLifecycleMixin, CombatMixin, MovementCollisionMixin, OverworldMixin, RenderingMixin, TeleportMixin, WindowMixin):
    def __init__(
        self,
        campaign: Campaign,
        *,
        episode: int = 1,
        level: int = 0,
        zoom: int = DEFAULT_ZOOM,
        visual_interpolation: bool = False,
        visual_interpolation_smoothing: bool = False,
    ) -> None:
        self.campaign = campaign
        self.episode_numbers = campaign.episode_numbers
        self.episode_index = max(0, self.episode_numbers.index(episode) if episode in self.episode_numbers else 0)
        self.level_index = level
        self.player = Player()
        self.last_world_position: tuple[float, float] | None = None
        self.completed_world_levels_by_episode: dict[int, set[int]] = {}
        self.world_entry_release_level: int | None = None
        # Reconstructed DS:6838/683A world-map camera registers.  Mission
        # camera still uses the generic helper below.
        self.world_camera_x = 0
        self.world_camera_y = 0
        self.keys: set[str] = set()
        self.collision_enabled = True
        self.show_codes = False
        self.show_unknown = False
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, int(zoom)))
        self.canvas_w = GAME_VIEW_W * self.zoom
        self.canvas_h = GAME_VIEW_H * self.zoom
        self.level_image: Image.Image | None = None
        self.foreground_image: Image.Image | None = None
        self.frame_photo: ImageTk.PhotoImage | None = None
        # Keep one persistent Tk canvas image item.  Recreating canvas items every
        # frame is surprisingly expensive at high zoom because Tk has to allocate,
        # map and redraw a large image item after every delete("all").
        self._frame_canvas_item: int | None = None
        self._frame_photo_size: tuple[int, int] | None = None
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
        # Camera registers are not updated by the DS:69F5 hard-death branch.
        # Store the mission camera at the moment the death state starts so the
        # renderer keeps the same viewport while the table-driven arc plays.
        self._death_camera: tuple[int, int] | None = None
        # Mirrors DS:69F6 for the separate DS:69F5 hard-death/bounce path.
        # Kept as an integer tick countdown instead of seconds.
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
        self._water_cells_cache: list | None = None
        self._laser_computer_last_warn_key: tuple[int, int, int, str] | None = None
        self._laser_field_source_keys_cache: set[tuple[int, int, int, str]] | None = None
        self._dynamic_source_keys_cache: set[tuple[int, int, int, str]] | None = None
        self._logic_accum = 0.0
        self._entity_accum = 0.0
        self.visual_interpolation_enabled = bool(visual_interpolation or visual_interpolation_smoothing)
        # Optional render-only stage 2. Linear interpolation remains the
        # baseline; smoothing changes only presentation positions with a short
        # display-space follow filter.
        self.visual_interpolation_smoothing = bool(visual_interpolation_smoothing)
        self._render_frame_id = 0
        # Render interpolation keeps a previous simulation pose and the current
        # fixed-tick pose.  Do not key this by Tk frame: if a slow UI frame has
        # to catch up by running two DOS ticks, the previous pose must become
        # the state before the *latest* fixed tick, not the state from the start
        # of the UI frame.  Otherwise the renderer lerps across multiple DOS
        # ticks at once and produces a visible hitch.
        self._prev_player_render_pos: tuple[float, float] = (self.player.x, self.player.y)
        self._prev_world_camera: tuple[float, float] = (float(self.world_camera_x), float(self.world_camera_y))
        self._prev_entity_render_pos: dict[int, tuple[float, float]] = {}
        self._last_render_dt = 1.0 / 60.0
        # Number of fixed actor ticks in the current Tk callback that already
        # captured the player's previous render pose. Actor slots can carry
        # the player (moving platforms), so player interpolation must use the
        # pose before the actor tick, not a later snapshot after the platform
        # has already snapped the player to its new fixed-tick position.
        self._collision_grid_cache = None
        self._collision_grid_cache_key = None
        self.anim_ticks = 0
        self._level_image_phase: int | None = None
        self._force_next_draw = True
        self.last_tick = time.perf_counter()
        self.sound = SoundPlayer.from_campaign(campaign, self.episode_number)

        self.root = tk.Tk()
        self.update_window_title()
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

    def load_level(self, *, reset_player: bool) -> None:
        self.teleport_release_cell = None
        self._death_camera = None
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
            self._death_camera = None
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
                self.init_world_camera_from_player()
            else:
                self.player = Player(*self.find_spawn())
        # Re-render after gameplay state has been reset.  This matters for
        # hidden platforms, collected cells and animated tile phase cache.
        self.rebuild_level_image()
        self.last_tick = time.perf_counter()
        self.reset_render_interpolation_state()
        self.draw()

    def rebuild_level_image(self) -> None:
        self._collision_grid_cache = None
        self._collision_grid_cache_key = None
        self._level_image_phase = None
        self.foreground_image = None
        self._teleporter_cells_cache = None
        self._water_cells_cache = None
        self._force_next_draw = True
        self.render_level_image_for_phase(self.current_tile_anim_tick())

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
        frame_start = time.perf_counter()
        self._render_frame_id += 1
        before_render_key = self.render_state_key()
        now = frame_start
        raw_dt = max(0.0, now - self.last_tick)
        self.last_tick = now
        self._last_render_dt = raw_dt

        # DOS_TICK_HZ is about 18.2065 Hz, i.e. one tick is roughly 54.9 ms.
        # The previous 1/20s clamp was only 50 ms, smaller than a real DOS
        # tick.  A late Tk callback at high zoom could therefore feed the fixed
        # timestep less than one full tick, producing an apparent off-by-one
        # hitch/slowdown instead of a normal catch-up update.  Clamp only very
        # long stalls so the game does not spiral after dragging the window or
        # hitting a breakpoint, but allow several genuine DOS ticks to catch up.
        fixed_dt = 1.0 / DOS_TICK_HZ
        dt = min(raw_dt, fixed_dt * 5.0)

        if self.is_world_map:
            self.update_world_player(dt)
        else:
            self.update_mission_simulation(dt)
        after_render_key = self.render_state_key()
        if self.visual_interpolation_enabled or self._force_next_draw or after_render_key != before_render_key:
            self._force_next_draw = False
            self.draw()

        # Schedule relative to the work already spent in this callback instead
        # of blindly waiting another 16 ms.  This keeps the render cadence close
        # to 60 Hz when drawing is cheap, and naturally drops frames rather than
        # queueing stale callbacks when a large zoom makes PhotoImage upload slow.
        frame_elapsed = time.perf_counter() - frame_start
        delay_ms = max(1, int(round((1.0 / 60.0 - frame_elapsed) * 1000)))
        self.root.after(delay_ms, self.tick)

    def render_state_key(self) -> tuple:
        """Cheap key for frames that would be visually identical without interpolation.

        The game simulation is fixed to the DOS timer, while Tk calls tick() near
        60 Hz.  When visual interpolation is off, redrawing the same 320x200
        framebuffer two extra times between DOS ticks only burns CPU, and the
        cost grows quadratically with zoom because the Tk image is larger.
        """
        p = self.player
        return (
            self.level_index,
            self.episode_number,
            self.is_world_map,
            int(p.x * 100),
            int(p.y * 100),
            p.facing,
            p.anim_state,
            p.walk_counter,
            bool(p.fire_pose_active),
            self.anim_ticks,
            self.current_tile_anim_tick(),
            self.player_dead_timer,
            self.player_death_frame_counter,
            self.teleport_active,
            self.teleport_timer_ticks,
            self.teleport_warped,
            int(self.hurt_flash * DOS_TICK_HZ),
            self.score,
            self.ammo,
            self.lives,
            len(self.collected_cells),
            len(self.opened_doors),
            len(self.opened_exit_doors),
            len(self.entities.projectiles),
            len(self.entities.explosions),
            len(self.entities.score_popups),
            self.has_glasses,
            self.has_floppy_disk,
            self.has_dynamite,
            self.laser_field_deactivated,
            self.show_codes,
            self.show_unknown,
            self.zoom,
            self.viewport_size(),
        )

    def water_cells(self):
        if self._water_cells_cache is None:
            info = self.episode.levels[self.level_index]
            self._water_cells_cache = [cell for cell in iter_map_cells(info) if cell.code == WATER_CODE]
        return self._water_cells_cache

    def update_mission_simulation(self, dt: float) -> None:
        """Advance one or more complete mission DOS ticks.

        Player and actor slots share one fixed presentation clock.  This matters
        most for moving platforms: the platform actor can carry the player
        before the player-control branch runs.  Snapshotting once before the
        whole fixed tick gives both the carried player and the platform the same
        linear ``previous -> current`` interval.
        """
        fixed_dt = 1.0 / DOS_TICK_HZ
        self._logic_accum = min(self._logic_accum + dt, fixed_dt * 5.0)
        # Keep the old entity accumulator as an alias for tools/debug helpers,
        # but rendering now uses the single logic accumulator for all dynamic
        # objects so actors and the player cannot drift by one presentation
        # phase.
        self._entity_accum = self._logic_accum

        while self._logic_accum >= fixed_dt:
            self._logic_accum -= fixed_dt
            self._entity_accum = self._logic_accum

            self.snapshot_dynamic_render_positions()
            self.snapshot_player_render_position()

            # The original game does not freeze actors/world animation while
            # DS:69F5 death state is active.  The top-level player branch at
            # SAM1:0x1A21 jumps into the death arc first, then continues to the
            # actor update call at SAM1:0x1B5D.  That ordering matters for
            # moving platforms: the platform branch can catch the freshly moved
            # death sprite on the same DOS tick.
            self.anim_ticks += 1

            if self.player_dead_timer > 0:
                self.update_player_death_tick()
                if self.player_dead_timer <= 0:
                    break
                self.update_entities_tick()
                self.update_barrel_overlap_state()
                self.update_exit_door_blasts()
            else:
                self.update_entities_tick()
                self.update_barrel_overlap_state()
                self.update_exit_door_blasts()
                self.update_player_tick()
                self.update_player_interactions(fixed_dt)

            self._entity_accum = self._logic_accum

    def update_player_death_tick(self) -> None:
        """Advance one fixed tick of the ASM DS:69F5/DS:69F6 death arc."""
        timer, active, signed_step = advance_death_bounce_tick(self.player_dead_timer)
        self.player_dead_timer = timer
        self.player_death_frame_counter += 1
        if active:
            # SAM1:0x1ABC..0x1AC0: word step is signed and then subtracted
            # from DS:34F0. Positive values move up, negative values move
            # down. This path deliberately ignores normal collision.
            self.player.y -= signed_step
            self.player.x = min(max(self.player.x, 0), LEVEL_W * TILE - PLAYER_W)
            # SAM1:0x1AC4..0x1AE5 clamps the death arc between absolute
            # screen/top Y=0x10 and the current camera register DS:683A+0xB8.
            # The death branch itself never advances the camera, so the player
            # falls until he hits the bottom of the already visible playfield
            # instead of dragging the viewport downward.
            cam_y = self._death_camera[1] if self._death_camera is not None else self.camera((self.player.x, self.player.y))[1]
            bottom_y = min(LEVEL_H * TILE - PLAYER_H, cam_y + 0xB8)
            self.player.y = min(max(self.player.y, 0x10), bottom_y)
        else:
            self.respawn_after_death()

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

        horizontal_step = (
            move_dir * horizontal_step_for_hold_ticks(p.move_hold_ticks, p.speed_bonus_step)
            if moving
            else 0
        )

        # SAM1:0xBC0E owns the normal vertical side of player motion.  Run the
        # fall/jump phase before accepting the horizontal destination probe so
        # the same-tick Y snap or one-pixel jump ascent is visible to the later
        # SAM1:0xB7D9 rectangle test.  This matters for one-tile openings: with
        # the old horizontal-first ordering, the player could be rejected by
        # the lower/upper corner one tick before BC0E aligned DS:34F0 to the
        # passage.
        if p.jump_anim_timer <= 0:
            p.fall_ticks, fall_step = advance_fall_tick(p.fall_ticks)
            self.move_player_fall_tick(fall_step)
            if jump and p.grounded and self.player_jump_headroom_clear():
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

        self.update_speed_bonus_tick()

        if horizontal_step:
            blocked = self.move_player_horizontal_tick(horizontal_step)
            if blocked and self.horizontal_block_resets_move_counter():
                # SAM1:0xB898 clears DS:681E only when DS:681C > 1.  The
                # reconstructed level model keeps level 0 as the overworld and
                # uses the original 1-based mission level number after that.
                p.move_hold_ticks = 0

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


    def horizontal_block_resets_move_counter(self) -> bool:
        # B7D9 does not always clear the acceleration counter on a blocked
        # horizontal destination probe.  It does so only under the DS:681C > 1
        # gate.  In this runtime level 0 is the overworld and mission indices
        # are the same 1-based values used by the EXE's level-state variable.
        return self.level_index > 1

    def player_jump_headroom_clear(self) -> bool:
        # SAM1:0xBC5E..0xBCB8 gates jump start before writing DS:6EC1.  It
        # probes runtime byte +0x1CC at Y-3 using the same player X samples
        # as B7D9 (x+3 and x+12).  If either probe is body-solid the space key
        # is ignored for this tick, so the player cannot start a jump into a
        # solid tile directly overhead.
        if not self.collision_enabled:
            return True
        p = self.player
        probe_y = int(p.y - 3) // TILE
        for sample_x in (int(p.x + 3), int(p.x + 12)):
            if self.cell_blocks_body(sample_x // TILE, probe_y):
                return False
        return True

    def update_speed_bonus_tick(self) -> None:
        p = self.player
        if p.speed_bonus_ticks <= 0:
            p.speed_bonus_step = 0
            p.speed_bonus_ticks = 0
            return
        p.speed_bonus_ticks -= 1
        if p.speed_bonus_ticks <= 0:
            p.speed_bonus_step = 0
            p.speed_bonus_ticks = 0

    def start_speed_bonus(self) -> None:
        # SAM1:0xD659..0xD65F: collecting runtime visual 0x0139 writes
        # DS:69A4=4 and DS:69A6=0x00D8.  The timer ISR decrements 69A6 once per
        # 0x14 ticks, so the fixed-tick runtime stores the expanded count.
        self.player.speed_bonus_step = PLAYER_SPEED_BONUS_STEP
        self.player.speed_bonus_ticks = PLAYER_SPEED_BONUS_TOTAL_TICKS

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
            if satellite.hit_flash_ticks > 0:
                satellite.hit_flash_ticks -= 1
            satellite.timer_ticks += 1
            if satellite.timer_ticks >= satellite.period_ticks:
                satellite.timer_ticks = 0
                satellite.frame_index = (satellite.frame_index + 1) % 4
        for platform in self.entities.platforms:
            # Moving-platform carry is in the actor branch around
            # SAM1:0x7FA6..0x8105, not in the normal player-control branch.
            # It does not test DS:69F5.  If the death arc has just moved the
            # player into the platform's narrow top contact rectangle, the EXE
            # still snaps DS:34F0 to actor_y-0x10 and carries DS:34EE by the
            # actor's DS:34E6 step.
            carry_player = self.platform_carry_contact_asm(platform)
            old_x = platform.x
            # Original actors use DS:34E6 as a literal per-tick pixel step.
            dx = platform.direction * platform.step_px
            platform.x += dx
            if self.platform_collides(platform):
                platform.x = old_x
                platform.direction *= -1
            elif carry_player:
                self.player.y = platform.y - PLAYER_H
                self.player.x += platform.x - old_x
                self.player.grounded = True
                self.player.fall_ticks = PLAYER_VERTICAL_COUNTER_INITIAL

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
                # EXE states 0x0A..0x0D do not walk.  DS:34DA is an elapsed
                # timer: SAM1:0x6B88/0x6C73 increments it first, compares it to
                # DS:34D8, and only resets it to zero after the row+front gate
                # succeeds and helper 0x5784 is called.  If the launcher is
                # already charged while the player is elsewhere, it should fire
                # immediately once the player enters its row and facing side.
                if enemy.alert_ticks > 0:
                    enemy.alert_ticks -= 1
                if self.rect_in_active_viewport(enemy.x, enemy.y, TILE, TILE):
                    period = max(1, enemy.shoot_interval_ticks)
                    enemy.shoot_timer_ticks = min(enemy.shoot_timer_ticks + 1, period)
                    if enemy.shoot_timer_ticks >= period and self.enemy_can_see_player(enemy):
                        enemy.shoot_timer_ticks = 0
                        self.spawn_enemy_projectile(enemy)
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
                    # for cases where the triggered blast actor overlaps the
                    # player after the initial trigger path.
                    self.kill_player()
                # SAM1:0x77E0..0x78A4 draws/clears the triggered mine's
                # short surrounding blast directly through the original draw
                # helpers.  It does not allocate extra projectile-impact
                # actors.  Older port builds approximated this by spawning
                # three persistent Explosion entities here, which made the
                # triggered mine visibly over-explode.  Keep the single
                # state-0x17 actor as the only runtime explosion object.
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
                if (
                    enemy.code == STATE2C_CONTACT_HAZARD_CODE
                    and self.contact_hazard_53c4_overlaps_player(enemy.x, enemy.y)
                    and self.hurt_flash <= 0
                ):
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
            if enemy.kind == "state1f_shooter":
                # SAM1:0x905C..0x977A. Raw 0x58/object 0x0331 is a two-high
                # bank-12 shooter with its own DS:34D6 frame ranges and the
                # same walk/stop/open phase fields used by the 0x24 helmet:
                #   DS:34D8 = 0x3C shot period, DS:34DA counts upward;
                #   DS:34DE = random(0x14)+0x3C walking phase;
                #   DS:34DC = 3 initially, then 0x1E stopped/open hold.
                # Direction +1 starts at frame counter 0x3D; direction -1
                # starts at 0x01.  While DS:34DE is non-zero, candidate X is
                # committed; when it reaches zero, the actor stays in place
                # and only advances/clamps its opening frame until DC refills
                # DE with 0x50.
                period = max(1, enemy.shoot_interval_ticks or 0x3C)
                enemy.shoot_timer_ticks += 1
                if enemy.shoot_timer_ticks >= period:
                    enemy.shoot_timer_ticks = 0
                    if self.enemy_can_see_player(enemy):
                        self.spawn_enemy_projectile(enemy)

                if enemy.phase_ticks > 0:
                    enemy.phase_ticks -= 1
                    if enemy.phase_ticks == 1:
                        enemy.aux_ticks = 0x1E
                        enemy.frame_counter = state1f_walk_counter_next(enemy.frame_counter, direction=enemy.direction, walking_phase=False)
                    else:
                        old_x = enemy.x
                        enemy.x += enemy.direction * enemy.step_px
                        blocked = (
                            self.enemy_collides(enemy)
                            or enemy.x < 0
                            or enemy.x + TILE > LEVEL_W * TILE
                            or not self.enemy_has_floor_ahead(enemy)
                        )
                        if blocked:
                            enemy.x = old_x
                            enemy.direction *= -1
                            enemy.frame_counter = state1f_walk_counter_start(enemy.direction)
                        else:
                            enemy.frame_counter = state1f_walk_counter_next(enemy.frame_counter, direction=enemy.direction, walking_phase=True)
                else:
                    enemy.frame_counter = state1f_walk_counter_next(enemy.frame_counter, direction=enemy.direction, walking_phase=False)
                    enemy.aux_ticks -= 1
                    if enemy.aux_ticks <= 0:
                        enemy.phase_ticks = 0x50
                        enemy.aux_ticks = 0x1E

                if self.enemy_overlaps_player(enemy) and self.hurt_flash <= 0:
                    self.hurt_player()
                if enemy.alert_ticks > 0:
                    enemy.alert_ticks -= 1
                continue
            if enemy.kind == "lightning_flyer":
                # State 0x26 / raw 0x6E is a drive-stop-lightning actor.  The
                # ASM branch (SAM1:0xA70F..0xA894) discards the candidate X while
                # its hold timer is active and creates object 0x0089 at
                # (actor_x, actor_y + 16).  Model this as a render-visible cycle:
                # drive for the DS:34D8-derived interval, stop while the
                # lightning actor is alive, then drive again.
                enemy.frame_counter = actor_walk_counter_next(enemy.frame_counter, direction=enemy.direction)
                if enemy.alert_ticks > 0:
                    enemy.alert_ticks -= 1
                    continue
                if enemy.aux_ticks > 0:
                    enemy.aux_ticks -= 1
                    if enemy.aux_ticks <= 0:
                        enemy.shoot_timer_ticks = max(1, enemy.shoot_interval_ticks)
                    continue

                old_x = enemy.x
                enemy.x += enemy.direction * enemy.step_px
                blocked = self.enemy_collides(enemy) or enemy.x < 0 or enemy.x + TILE > LEVEL_W * TILE
                if blocked:
                    enemy.x = old_x
                    enemy.direction *= -1
                    enemy.frame_counter = actor_walk_counter_next(0, direction=enemy.direction)

                if enemy.shoot_timer_ticks > 0:
                    enemy.shoot_timer_ticks -= 1
                if enemy.shoot_timer_ticks <= 0:
                    self.spawn_lightning_bolt(enemy)
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
                if self.contact_hazard_53c4_overlaps_player(enemy.x, enemy.y) and self.hurt_flash <= 0:
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
            if enemy.alert_ticks > 0:
                enemy.alert_ticks -= 1
            if enemy.kind == "ceiling_laser" and enemy.can_shoot:
                # SAM1:0x9A25 increments DS:34DA.  At DS:34DA == DS:34D8 it
                # tests whether the player origin is inside actor_x +/- 16 and
                # below the crawler.  If the test fails, SAM1:0x9AB2 decrements
                # the timer back to period-1, so the shooter remains armed and
                # fires on the first valid tick after the player walks underneath.
                period = max(1, enemy.shoot_interval_ticks)
                enemy.shoot_timer_ticks = min(enemy.shoot_timer_ticks + 1, period)
                if enemy.shoot_timer_ticks >= period:
                    if self.enemy_can_see_player(enemy):
                        self.spawn_enemy_projectile(enemy)
                        enemy.shoot_timer_ticks = 0
                    else:
                        enemy.shoot_timer_ticks = period - 1
                # The same state-0x21 branch immediately calls helper 0x53C4
                # with (actor_x, actor_y), so touching the crawler body causes
                # generic player damage even when no laser was emitted.
                if self.contact_hazard_53c4_overlaps_player(enemy.x, enemy.y) and self.hurt_flash <= 0:
                    self.hurt_player()
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















































    def update_player_interactions(self, dt: float) -> None:
        self.check_teleporter_touch()
        self.collect_touching_codes()
        self.check_exit_door_touch()
        self.collect_rip_enemies()
        self.check_hard_death_tile_touch()
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
                    if cell.code == SPEED_BONUS_CODE:
                        self.start_speed_bonus()
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
        completed_level = self.level_index
        self.last_world_position = self.last_world_position or self.find_world_spawn()
        if completed_level > 0:
            self.completed_world_levels().add(completed_level)
            self.world_entry_release_level = completed_level
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

    @staticmethod
    def runtime_visual_ids_for_code(code: int) -> frozenset[int]:
        return frozenset(write.cA for write in runtime_cell_writes_for_code(code) if write.cA)

    def check_hard_death_tile_touch(self) -> None:
        # The interaction dispatcher does not only test raw map bytes.  It runs
        # after the cell byte has been translated to a runtime cA visual id;
        # SAM1:0xD221..0xD254 then kills the player on 0x01F3 (water 0x60),
        # 0x025B, 0x0265, 0x0267 and 0x0268.  This catches water and the other
        # immediate-death source tiles that were previously just decorative.
        if self.is_world_map or self.player_dead_timer > 0:
            return
        p = self.player
        left, top = p.x, p.y
        right, bottom = p.x + PLAYER_W - 1, p.y + PLAYER_H - 1
        for cell in self.player_overlapping_cells():
            key = self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
            if key in self.collected_cells or key in self.opened_doors or key in self.opened_exit_doors:
                continue
            if cell.code == LASER_FIELD_CODE and (self.laser_field_deactivated or not self.laser_field_visible()):
                continue
            if not (self.runtime_visual_ids_for_code(cell.code) & HARD_DEATH_RUNTIME_VISUAL_IDS):
                continue
            hx1 = cell.x * TILE + 2
            hy1 = cell.y * TILE + 2
            hx2 = cell.x * TILE + TILE - 3
            hy2 = cell.y * TILE + TILE - 3
            if right < hx1 or left > hx2 or bottom < hy1 or top > hy2:
                continue
            self.kill_player()
            return

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

    def enemy_body_contact_uses_generic_hurt(self, enemy) -> bool:
        """Return whether the broad fallback body-contact pass may hurt.

        Do not infer damage from the fact that an actor is called an enemy.
        Several decoded actor branches own their contact policy explicitly;
        running the old broad fallback over them created false touch damage.
        Raw 0x51/0x52 stationary launchers (objects 0x01D1/0x01D0) are hostile
        through the emitted 0x01D6 projectile, not by body contact.
        """
        if enemy.is_rip:
            return False
        if enemy.kind in {
            "stationary_shooter",
            "state2b_anim",
            "state2c_anim",
            "state17_landmine",
            "state23_contact_bomb",
            "state29_money_bag",
        }:
            return False
        return True

    def check_enemy_touch(self, dt: float) -> None:
        if self.hurt_flash > 0:
            self.hurt_flash = max(0.0, self.hurt_flash - dt)
            return
        p = self.player
        left, top = p.x, p.y
        right, bottom = p.x + PLAYER_W - 1, p.y + PLAYER_H - 1
        for enemy in self.entities.enemies:
            if not OpenAgentApp.enemy_body_contact_uses_generic_hurt(self, enemy):
                continue
            if right < enemy.x or left > enemy.x + TILE - 1:
                continue
            if bottom < enemy.y or top > enemy.y + TILE - 1:
                continue
            # Generic enemy body contact routes through the hurt helper, not
            # the hard-death tile dispatcher.  It removes one life and starts
            # the 0x1E-tick invulnerability window.  Actor families with an
            # ASM-specific contact branch are excluded before this fallback.
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



def default_source() -> Path:
    for candidate in (PROJECT_ROOT / "game_data", PROJECT_ROOT / "game_data" / "game_data.zip", PROJECT_ROOT / "game_data.zip"):
        if candidate.exists():
            return candidate
    return PROJECT_ROOT / "game_data"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the OpenAgent prototype engine.")
    parser.add_argument("source", nargs="?", type=Path, default=default_source(), help="game_data folder or ZIP")
    parser.add_argument("--episode", type=int, default=1, choices=(1, 2, 3))
    parser.add_argument("--level", type=int, default=0)
    parser.add_argument("--zoom", type=int, default=DEFAULT_ZOOM, help="initial integer zoom, default 2 for a 320x200 DOS viewport")
    parser.add_argument("--interpolate-render", action="store_true", help="linearly interpolate render positions between fixed DOS ticks")
    parser.add_argument("--smooth-render", action="store_true", help="use optional render-only presentation smoothing")
    args = parser.parse_args(argv)

    campaign = load_campaign(args.source)
    app = OpenAgentApp(
        campaign,
        episode=args.episode,
        level=args.level,
        zoom=args.zoom,
        visual_interpolation=args.interpolate_render or args.smooth_render,
        visual_interpolation_smoothing=args.smooth_render,
    )
    app.run()
    return 0
