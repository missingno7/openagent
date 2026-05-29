from __future__ import annotations

import argparse
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

from .animation import (
    PLAYER_FIRE_HOLD_SECONDS,
    PLAYER_STATE_FIRE_LEFT,
    PLAYER_STATE_FIRE_RIGHT,
    PLAYER_STATE_IDLE_LEFT,
    PLAYER_STATE_IDLE_RIGHT,
    PLAYER_STATE_JUMP_RIGHT,
    PLAYER_STATE_JUMP_LEFT,
    PLAYER_STATE_WALK_LEFT,
    PLAYER_STATE_WALK_RIGHT,
    PLAYER_WALK_COUNTER_MAX,
    PLAYER_WALK_COUNTER_START,
    PLAYER_WALK_COUNTER_STEP,
    player_tile,
    actor_walk_counter_next,
    walker_tile,
    bank14_guard_tile,
)
from .collision import PLAYER_COLLISION_BOTTOM, PLAYER_DRAW_H, PLAYER_DRAW_W, player_body_probes
from .entities import LevelEntities, MovingPlatform, Projectile, ScorePopup, extract_level_entities
from .exe_actor_mechanics import (
    BANK14_GUARD_BEHAVIOUR_BY_BASE_TILE,
    BANK14_GUARD_SHOOT_TIMER_RANGE_BY_BASE_TILE,
    BANK14_GUARD_SPEED_BY_BASE_TILE,
    deterministic_range,
)
from .level_model import build_runtime_collision_grid, cells_at, codes_at, iter_map_cells
from .loader import Campaign, ensure_editor_importable, load_campaign
from .semantics import (
    ACTIVE_HIDDEN_PLATFORM_COLLISION_CODE,
    BANK14_GUARD_CODE_BY_BASE_TILE,
    BANK14_RIP_PICKUP_SCORE,
    BANK14_RIP_SHOT_SCORE,
    BANK14_RIP_TILE,
    GLASSES_CODE,
    HIDDEN_PLATFORM_CODE,
    MISSION_PLAYER_START_CODE,
    WORLD_BLOCKED_CODES,
    WORLD_ENTRANCE_CODES,
    WORLD_PLAYER_CODE,
    door_unlocked_by,
    is_collectible_code,
    is_door_code,
    is_dynamic_mission_code,
    is_mission_code_body_solid,
    is_mission_code_floor_solid,
    is_one_way_platform_code,
    mission_code_kind,
    score_popup_tile_for_value,
    score_value_for_code,
)

ROOT = Path(__file__).resolve().parents[1]
ensure_editor_importable(ROOT)

from secret_agent_editor.constants import LEVEL_H, LEVEL_W, ROW_BYTES, TILE
from secret_agent_editor.render import SecretAgentRenderer


GAME_VIEW_W = 320
GAME_VIEW_H = 200
DEFAULT_ZOOM = 2
MIN_ZOOM = 1
MAX_ZOOM = 6
HUD_H = 54
PLAYER_W = PLAYER_DRAW_W
PLAYER_H = PLAYER_DRAW_H
# The EXE horizontal path calls routine 0x532D to choose DS:6820 and then adds
# that integer pixel step to DS:34EE. The game logic is paced like a DOS timer
# tick, not like a 60 Hz modern render loop; running these pixel steps at 60 Hz
# made the player much too fast.
DOS_TICK_HZ = 18.2065
WORLD_MOVE_SPEED = 72.0
# EXE routine 0x532D accelerates horizontal movement by selecting integer
# DS:6820 steps.  The normal path is 1 px/tick for ticks 1..2, 2 px/tick at
# tick 3, 4 px/tick for ticks 4..6, then 4 + DS:69A4 afterwards.
PLAYER_STEP_RAMP = ((1, 2, 1), (3, 3, 2), (4, 6, 4), (7, 1000, 8))
# The EXE does not have a separate continuous velocity/gravity model.  Both
# jump ascent and falling use the same byte table at DS:34AF.  Routine BC0E
# starts a jump by setting DS:6EC1=1 and DS:34EA=0.  While DS:6EC1 is set,
# each tick increments DS:34EA and moves the player upward by -table[34EA].
# At DS:34EA == 0x0A it clears DS:6EC1 and leaves DS:34EA at 9, so the next
# fall tick resumes at table[10].  Routine B8B3 then increments DS:34EA up to
# 0x13 and moves the player downward by +table[34EA].
JUMP_ASCENT_END_COUNTER = 0x0A
FALL_COUNTER_MAX = 0x13
PLAYER_VERTICAL_STEP_TABLE = (
    0,
    8, 8, 8, 4, 4, 2, 2, 2, 1, 1, 2, 2, 2, 4, 4, 8, 8, 8, 8,
)
GROUND_EPSILON = 0.35


@dataclass
class Player:
    x: float = 32.0
    y: float = 32.0
    vx: float = 0.0
    vy: float = 0.0
    grounded: bool = False
    facing: int = 1
    walk_time: float = 0.0
    walk_counter: int = PLAYER_WALK_COUNTER_START
    anim_state: int = PLAYER_STATE_IDLE_RIGHT
    firing_time: float = 0.0
    fire_cooldown: float = 0.0
    fire_held: bool = False
    fire_pose_active: bool = False
    # Mirrors EXE DS:6EC1.  The vertical counter itself is fall_ticks/DS:34EA.
    jump_anim_timer: int = 0
    fall_ticks: int = 0
    move_hold_ticks: int = 0
    last_move_dir: int = 0


class OpenAgentApp:
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
        self.canvas_h = GAME_VIEW_H * self.zoom + HUD_H
        self.level_image: Image.Image | None = None
        self.level_photo: ImageTk.PhotoImage | None = None
        self.frame_photo: ImageTk.PhotoImage | None = None
        self.entities = LevelEntities([], [], [], [])
        self.collected_cells: set[tuple[int, int, int, str]] = set()
        self.opened_doors: set[tuple[int, int, int, str]] = set()
        self.owned_keys: set[int] = set()
        self.score = 0
        self.ammo = 0
        self.hurt_flash = 0.0
        self.has_glasses = False
        self._logic_accum = 0.0
        self._entity_accum = 0.0
        self._collision_grid_cache = None
        self._collision_grid_cache_key = None
        self.last_tick = time.perf_counter()

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
        self.campaign.cleanup()
        self.root.destroy()

    def on_key_press(self, event: tk.Event) -> None:
        key = event.keysym
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
            self.root.geometry(f"{view_w * self.zoom}x{view_h * self.zoom + HUD_H}")
            self.draw()

    def viewport_size(self) -> tuple[int, int]:
        # Canvas pixels are output pixels.  Divide by zoom to get original DOS
        # logical pixels.  The default 320x200 at 2x mirrors the game viewport,
        # while resizing the window shows a larger/smaller camera crop.
        logical_w = max(160, self.canvas_w // max(1, self.zoom))
        logical_h = max(100, (self.canvas_h - HUD_H) // max(1, self.zoom))
        return logical_w, logical_h

    def change_episode(self, delta: int) -> None:
        self.episode_index = (self.episode_index + delta) % len(self.episode_numbers)
        self.level_index = min(self.level_index, self.level_count - 1)
        self.load_level(reset_player=True)

    def change_level(self, delta: int) -> None:
        self.level_index = (self.level_index + delta) % self.level_count
        self.load_level(reset_player=True)

    def load_level(self, *, reset_player: bool) -> None:
        renderer = SecretAgentRenderer(self.episode)
        self.rebuild_level_image()
        self.entities = LevelEntities([], [], [], []) if self.is_world_map else extract_level_entities(self.episode.levels[self.level_index])
        if reset_player and not self.is_world_map:
            self.collected_cells.clear()
            self.opened_doors.clear()
            self.owned_keys.clear()
            self.score = 0
            self.ammo = 0
            self.hurt_flash = 0.0
            self.has_glasses = False
        if reset_player:
            if self.is_world_map:
                spawn = self.last_world_position or self.find_world_spawn()
                self.player = Player(spawn[0], spawn[1])
            else:
                self.player = Player(*self.find_spawn())
        self.last_tick = time.perf_counter()
        self.draw()

    def rebuild_level_image(self) -> None:
        renderer = SecretAgentRenderer(self.episode)
        self._collision_grid_cache = None
        self._collision_grid_cache_key = None
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
            skip_cells = set(self.collected_cells) | set(self.opened_doors)
        self.level_image = renderer.render(
            self.level_index,
            zoom=1,
            show_codes=self.show_codes,
            show_unknown=self.show_unknown,
            skip_codes=skip_codes,
            skip_cells=skip_cells,
        )

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

    def find_world_spawn(self) -> tuple[float, float]:
        info = self.episode.levels[0]
        for cell in iter_map_cells(info):
            if cell.code == WORLD_PLAYER_CODE:
                return float(cell.x * TILE + 2), float(cell.y * TILE + 1)
        return 32.0, 32.0

    def world_entrances(self) -> list[tuple[int, int, int]]:
        entrances = []
        for cell in iter_map_cells(self.episode.levels[0]):
            if cell.code in WORLD_ENTRANCE_CODES:
                entrances.append((cell.x, cell.y, len(entrances) + 1))
        return entrances

    def iter_visual_codes(self, level_index: int):
        for cell in iter_map_cells(self.episode.levels[level_index]):
            yield cell.x, cell.y, cell.code

    def tick(self) -> None:
        now = time.perf_counter()
        dt = min(now - self.last_tick, 1 / 20)
        self.last_tick = now
        if self.is_world_map:
            self.update_world_player(dt)
        else:
            self.update_entities(dt)
            self.update_player(dt)
            self.update_player_interactions(dt)
        self.draw()
        self.root.after(16, self.tick)

    def update_world_player(self, dt: float) -> None:
        p = self.player
        left = any(k in self.keys for k in ("Left", "a", "A"))
        right = any(k in self.keys for k in ("Right", "d", "D"))
        up = any(k in self.keys for k in ("Up", "w", "W"))
        down = any(k in self.keys for k in ("Down", "s", "S"))
        self.move_world_axis((right - left) * WORLD_MOVE_SPEED * dt, 0.0)
        self.move_world_axis(0.0, (down - up) * WORLD_MOVE_SPEED * dt)
        self.last_world_position = (p.x, p.y)

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

    def world_player_blocked(self) -> bool:
        p = self.player
        probes = [
            (p.x + 2, p.y + 2),
            (p.x + PLAYER_W - 3, p.y + 2),
            (p.x + 2, p.y + PLAYER_H - 3),
            (p.x + PLAYER_W - 3, p.y + PLAYER_H - 3),
        ]
        return any(self.world_cell_blocked(int(x) // TILE, int(y) // TILE) for x, y in probes)

    def world_cell_blocked(self, x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
            return True
        info = self.episode.levels[0]
        cell_codes = [code for code in codes_at(info, x, y) if code not in (0, 0x20, ord("*"))]
        if not cell_codes:
            return False
        return any(code in WORLD_BLOCKED_CODES for code in cell_codes)

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
            self.load_level(reset_player=True)

    def update_player(self, dt: float) -> None:
        # Keep the mission player on DOS-like fixed ticks.  The previous
        # continuous vy/gravity approximation could move by a fractional amount,
        # resolve by a while loop, then sample the same one-way tile again and
        # appear to fall through or freeze.
        self._logic_accum = min(self._logic_accum + dt, 0.15)
        while self._logic_accum >= 1.0 / DOS_TICK_HZ:
            self._logic_accum -= 1.0 / DOS_TICK_HZ
            self.update_player_tick()

    @staticmethod
    def ramp_value(ticks: int, ramp: tuple[tuple[int, int, int], ...]) -> int:
        for start, end, value in ramp:
            if start <= ticks <= end:
                return value
        return ramp[-1][2]

    def update_player_tick(self) -> None:
        p = self.player
        left = any(k in self.keys for k in ("Left", "a", "A"))
        right = any(k in self.keys for k in ("Right", "d", "D"))
        jump = "space" in self.keys
        fire = any(k in self.keys for k in ("Control_L", "Control_R", "Control"))

        move_dir = (1 if right else 0) - (1 if left else 0)
        moving = move_dir != 0
        if moving:
            p.facing = 1 if move_dir > 0 else -1
            if move_dir != p.last_move_dir:
                p.move_hold_ticks = 0
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
            self.move_axis_pixels(move_dir * self.ramp_value(p.move_hold_ticks, PLAYER_STEP_RAMP), 0)

        self.refresh_grounded_state()
        if jump and p.grounded and p.jump_anim_timer <= 0:
            p.grounded = False
            p.fall_ticks = 0
            p.jump_anim_timer = 1

        if p.jump_anim_timer > 0:
            # EXE DS:6EC1 jump phase.  Use the same DS:34AF table as falling,
            # but subtract the displacement from Y.  At counter 0x0A the EXE
            # clears DS:6EC1 and keeps DS:34EA at 9, making the next fall tick
            # use table[10] rather than restarting from a fast 8px step.
            p.fall_ticks = min(FALL_COUNTER_MAX, p.fall_ticks + 1)
            if p.fall_ticks == JUMP_ASCENT_END_COUNTER:
                p.jump_anim_timer = 0
                p.fall_ticks = JUMP_ASCENT_END_COUNTER - 1
            elif p.fall_ticks < len(PLAYER_VERTICAL_STEP_TABLE):
                blocked = self.move_axis_pixels(0, -PLAYER_VERTICAL_STEP_TABLE[p.fall_ticks])
                if blocked:
                    p.jump_anim_timer = 0
                    p.fall_ticks = JUMP_ASCENT_END_COUNTER - 1
        else:
            if not p.grounded:
                p.fall_ticks = min(FALL_COUNTER_MAX, p.fall_ticks + 1)
                fall_step = PLAYER_VERTICAL_STEP_TABLE[p.fall_ticks]
                self.move_axis_pixels(0, fall_step)

        self.refresh_grounded_state()
        self.update_player_anim_state(moving=moving)

        max_x = LEVEL_W * TILE - PLAYER_W
        max_y = LEVEL_H * TILE - PLAYER_H
        p.x = min(max(p.x, 0), max_x)
        if p.y > max_y:
            p.y = float(max_y)
            p.vy = 0
            p.grounded = True
            p.jump_anim_timer = 0
            p.fall_ticks = 0
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
            self.update_entities_tick()
        self.update_projectiles(dt)

    def update_entities_tick(self) -> None:
        dt = 1.0 / DOS_TICK_HZ
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
            if enemy.is_rip:
                continue
            enemy.frame_counter = actor_walk_counter_next(enemy.frame_counter, direction=enemy.direction)
            old_x = enemy.x
            enemy.x += enemy.direction * enemy.step_px
            if self.enemy_collides(enemy) or not self.enemy_has_floor_ahead(enemy):
                enemy.x = old_x
                enemy.direction *= -1
                enemy.frame_counter = actor_walk_counter_next(0, direction=enemy.direction)
            if enemy.alert_ticks > 0:
                enemy.alert_ticks -= 1
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

        kept_popups: list[ScorePopup] = []
        for popup in self.entities.score_popups:
            popup.ticks_left -= 1
            popup.y -= 1
            if popup.ticks_left > 0:
                kept_popups.append(popup)
        self.entities.score_popups = kept_popups

    def move_axis_pixels(self, dx: int | float, dy: int | float) -> bool:
        """Move at integer DOS-pixel granularity and return True if blocked."""
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
                if self.player_collides():
                    p.x -= step
                    blocked = True
                    break
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
                    if self.player_floor_blocked(prev_bottom, new_bottom) or self.player_on_platform():
                        landing_y = self.player_landing_y(prev_bottom, new_bottom)
                        if landing_y is not None:
                            p.y = landing_y
                        else:
                            p.y -= step
                        p.grounded = True
                        p.jump_anim_timer = 0
                        p.fall_ticks = 0
                        blocked = True
                        break
                    p.grounded = False
        return blocked

    def move_axis(self, dx: float, dy: float) -> None:
        # Compatibility wrapper for older callers.  Mission player movement now
        # uses move_axis_pixels() so collision is checked one DOS pixel at a time.
        self.move_axis_pixels(dx, dy)


    def update_player_anim_state(self, *, moving: bool) -> None:
        p = self.player
        if p.fire_held and p.fire_pose_active:
            p.anim_state = PLAYER_STATE_FIRE_LEFT if p.facing < 0 else PLAYER_STATE_FIRE_RIGHT
            return
        # Original jump frames 0x0F/0x10 are tied to DS:69F5/69F6.  Do not use
        # them merely because the player is airborne; falling from an edge keeps
        # the normal facing/idle/walk state.
        if p.jump_anim_timer > 0:
            # Bank 13 only has two non-death jump frames here: right and left.
            # Do not toggle into the following death frames.
            p.anim_state = PLAYER_STATE_JUMP_LEFT if p.facing < 0 else PLAYER_STATE_JUMP_RIGHT
            return
        if moving:
            p.anim_state = PLAYER_STATE_WALK_LEFT if p.facing < 0 else PLAYER_STATE_WALK_RIGHT
        else:
            p.anim_state = PLAYER_STATE_IDLE_LEFT if p.facing < 0 else PLAYER_STATE_IDLE_RIGHT

    def refresh_grounded_state(self) -> None:
        p = self.player
        if not self.collision_enabled:
            return
        # Ground support is not tested by asking whether the current bottom
        # pixel overlaps the floor.  The EXE-style probes look one pixel below
        # the 16 px player box.  The previous +/- epsilon check missed the
        # exact landing coordinate (bottom == tile_top - 1), so jump input often
        # saw grounded=False and could never start.
        bottom = p.y + PLAYER_COLLISION_BOTTOM
        landing_y = self.player_landing_y(bottom, bottom + 1.01)
        platform = self.platform_below()
        if landing_y is not None and abs(p.y - landing_y) <= 1.0:
            p.y = landing_y
            p.vy = 0
            p.grounded = True
            if p.jump_anim_timer <= 0:
                p.fall_ticks = 0
            return
        if platform is not None and abs((p.y + PLAYER_H) - platform.y) <= 1.0:
            p.y = platform.y - PLAYER_H
            p.vy = 0
            p.grounded = True
            if p.jump_anim_timer <= 0:
                p.fall_ticks = 0
            return
        # If the two foot probes no longer see +0x1CD/+0x1CC under the player,
        # falling starts. This keeps ledges working while still allowing jumping
        # from an exact tile-top standing position.
        p.grounded = False

    def player_landing_y(self, prev_bottom: float, new_bottom: float) -> float | None:
        p = self.player
        candidates: list[float] = []
        for sample_x in (int(p.x + 3), int(p.x + 12)):
            tile_x = sample_x // TILE
            tile_y = int(new_bottom) // TILE
            if self.cell_blocks_floor(tile_x, tile_y, prev_bottom=prev_bottom, new_bottom=new_bottom):
                candidates.append(float(tile_y * TILE - PLAYER_COLLISION_BOTTOM - 1))
        platform = self.platform_below()
        if platform is not None:
            candidates.append(float(platform.y - PLAYER_H))
        return min(candidates) if candidates else None

    def player_collides(self) -> bool:
        p = self.player
        for probe in player_body_probes(p.x, p.y):
            if self.cell_blocks_body(probe.tile_x, probe.tile_y):
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
        return set(self.collected_cells) | set(self.opened_doors)

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
        cell = self.runtime_collision_cell(x, y)
        if cell is None:
            return False
        if is_door_code(cell.source_code):
            return door_unlocked_by(cell.source_code) not in self.owned_keys
        return cell.body_solid

    def cell_blocks_floor(self, x: int, y: int, *, prev_bottom: float, new_bottom: float) -> bool:
        if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
            return True
        cell = self.runtime_collision_cell(x, y)
        if cell is None:
            return False
        if is_door_code(cell.source_code):
            return door_unlocked_by(cell.source_code) not in self.owned_keys
        if cell.body_solid:
            return True
        if cell.foot_solid:
            tile_top = y * TILE
            return prev_bottom <= tile_top + 1 and new_bottom >= tile_top
        return False

    def runtime_cell_key(self, x: int, y: int, code: int, layer: str) -> tuple[int, int, int, str]:
        return (x, y, code, layer)


    def try_fire_projectile(self) -> bool:
        p = self.player
        if p.fire_cooldown > 0:
            return False
        # The EXE fire-key branch checks DS:6EC1/69F5 and skips shot creation
        # while the jump routine is active.  It also exits before changing
        # DS:3500 when there are no shots available.
        if p.jump_anim_timer > 0:
            p.fire_cooldown = 0.10
            return False
        if self.ammo <= 0:
            p.fire_cooldown = 0.18
            return False
        self.ammo -= 1
        p.fire_cooldown = 0.22
        start_x = p.x + (PLAYER_W - 1 if p.facing > 0 else -2)
        start_y = p.y + 7
        self.entities.projectiles.append(Projectile(start_x, start_y, p.facing, hostile=False))
        return True

    def enemy_can_see_player(self, enemy) -> bool:
        """Approximate the EXE guard firing gate.

        The SAM1 branch around 0x63CD first compares the actor and player tile
        rows, then checks whether the player lies in front of DS:34E2 before
        calling projectile helper 0x5784.  Treat body-solid cells between the
        guard and player as blocking line of sight.
        """
        if not enemy.can_shoot:
            return False
        p = self.player
        enemy_row = int(enemy.y + 8) // TILE
        player_row = int(p.y + PLAYER_COLLISION_BOTTOM // 2) // TILE
        if enemy_row != player_row:
            return False
        if enemy.direction > 0 and p.x <= enemy.x:
            return False
        if enemy.direction < 0 and p.x >= enemy.x:
            return False
        start = int(enemy.x + (TILE if enemy.direction > 0 else -1)) // TILE
        end = int(p.x + PLAYER_W // 2) // TILE
        step = 1 if end >= start else -1
        for tile_x in range(start, end + step, step):
            if self.cell_blocks_body(tile_x, enemy_row):
                return False
        return True

    def bank14_shot_hits_back(self, enemy, shot: Projectile) -> bool:
        if enemy.bank != 14 or enemy.base_tile is None or enemy.is_rip:
            return False
        # If the bullet travels in the same direction the guard is facing, it
        # reached him from behind.  The game responds by making him face the
        # player, which is visible with bank-14 shooters.
        return shot.direction == enemy.direction

    def spawn_enemy_projectile(self, enemy) -> None:
        # Bank-14 shooter guards use the same light actor-slot behaviour as the
        # simple walkers, plus a periodic horizontal shot.  The EXE stores their
        # active sprite in DS:34E0 and uses variants 24/32 as shooters; this
        # prototype mirrors the visible behaviour while the exact projectile
        # slot table is still being mapped.
        start_x = enemy.x + (TILE - 2 if enemy.direction > 0 else -2)
        start_y = enemy.y + 8
        self.entities.projectiles.append(Projectile(start_x, start_y, enemy.direction, speed=115.0, hostile=True))

    def update_projectiles(self, dt: float) -> None:
        kept: list[Projectile] = []
        for shot in self.entities.projectiles:
            shot.x += shot.direction * shot.speed * dt
            tile_x = int(shot.x) // TILE
            tile_y = int(shot.y) // TILE
            if tile_x < 0 or tile_y < 0 or tile_x >= LEVEL_W or tile_y >= LEVEL_H:
                continue
            if self.cell_blocks_body(tile_x, tile_y):
                continue
            if shot.hostile:
                if self.projectile_hits_player(shot):
                    self.hurt_flash = 0.75
                    continue
                kept.append(shot)
                continue
            hit = None
            for enemy in self.entities.enemies:
                if enemy.x - 1 <= shot.x <= enemy.x + TILE and enemy.y <= shot.y <= enemy.y + TILE - 1:
                    hit = enemy
                    break
            if hit is not None:
                self.hit_enemy_with_projectile(hit, shot)
                continue
            kept.append(shot)
        self.entities.projectiles = kept

    def projectile_hits_player(self, shot: Projectile) -> bool:
        p = self.player
        return p.x <= shot.x <= p.x + PLAYER_W - 1 and p.y <= shot.y <= p.y + PLAYER_H - 1

    def spawn_score_popup(self, x: float, y: float, value: int, *, preferred_tile: int | None = None) -> None:
        popup_tile = preferred_tile if preferred_tile is not None else score_popup_tile_for_value(value)
        if popup_tile is None:
            # The original popup sprite set only has fixed denominations up to
            # 10K; use the largest visible score marker for larger bonuses.
            popup_tile = score_popup_tile_for_value(10000)
        if popup_tile is not None:
            self.entities.score_popups.append(ScorePopup(float(x), float(y - 8), value, popup_tile))

    def hit_enemy_with_projectile(self, enemy, shot: Projectile | None = None) -> None:
        if enemy.is_rip:
            self.entities.enemies.remove(enemy)
            self.score += BANK14_RIP_SHOT_SCORE
            self.spawn_score_popup(enemy.x, enemy.y, BANK14_RIP_SHOT_SCORE)
            return
        if enemy.bank == 14 and enemy.base_tile is not None:
            hit_from_back = shot is not None and self.bank14_shot_hits_back(enemy, shot)

            # The back-shot observation is part of the hit reaction, not a
            # separate non-damaging warning.  In the original actor path the
            # projectile still enters the same interaction/damage pipeline; the
            # visible extra effect is that DS:34E2 is rewritten so the guard
            # faces the player after being hit from behind.
            if hit_from_back:
                enemy.direction *= -1
                enemy.alert_ticks = 12

            if enemy.base_tile > 0:
                enemy.base_tile -= 8
                enemy.code = BANK14_GUARD_CODE_BY_BASE_TILE.get(enemy.base_tile, enemy.code)
                enemy.step_px = BANK14_GUARD_SPEED_BY_BASE_TILE.get(enemy.base_tile, enemy.step_px)
                enemy.behavior_state = BANK14_GUARD_BEHAVIOUR_BY_BASE_TILE.get(enemy.base_tile, enemy.behavior_state)
                shoot_range = BANK14_GUARD_SHOOT_TIMER_RANGE_BY_BASE_TILE.get(enemy.base_tile)
                if shoot_range is not None:
                    enemy.shoot_interval_ticks = deterministic_range(
                        enemy.code, int(enemy.x) // TILE, int(enemy.y) // TILE, shoot_range[0], shoot_range[1], salt=2
                    )
                    enemy.shoot_timer_ticks = min(enemy.shoot_timer_ticks, enemy.shoot_interval_ticks) or enemy.shoot_interval_ticks
                else:
                    enemy.shoot_interval_ticks = 0
                    enemy.shoot_timer_ticks = 0
                enemy.frame_counter = actor_walk_counter_next(0, direction=enemy.direction)
                return

            enemy.kind = "rip"
            enemy.base_tile = BANK14_RIP_TILE
            enemy.step_px = 0
            enemy.shoot_interval_ticks = 0
            enemy.shoot_timer_ticks = 0
            enemy.frame_counter = 0
            return
        self.entities.enemies.remove(enemy)
        self.score += 100
        self.spawn_score_popup(enemy.x, enemy.y, 100)

    def enemy_collides(self, enemy) -> bool:
        left = int(enemy.x) // TILE
        right = int(enemy.x + TILE - 1) // TILE
        top = int(enemy.y) // TILE
        bottom = int(enemy.y + TILE - 1) // TILE
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                if self.cell_blocks_body(x, y):
                    return True
        return False

    def enemy_has_floor_ahead(self, enemy) -> bool:
        foot_x = int(enemy.x + (TILE if enemy.direction > 0 else -1)) // TILE
        foot_y = int(enemy.y + TILE) // TILE
        if foot_x < 0 or foot_x >= LEVEL_W or foot_y < 0 or foot_y >= LEVEL_H:
            return False
        cell = self.runtime_collision_cell(foot_x, foot_y)
        return bool(cell and (cell.body_solid or cell.foot_solid))

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

    def player_on_platform(self) -> bool:
        return self.platform_below() is not None

    def update_player_interactions(self, dt: float) -> None:
        self.collect_touching_codes()
        self.collect_rip_enemies()
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
            if key in self.collected_cells or key in self.opened_doors:
                continue
            kind = mission_code_kind(cell.code)
            if is_collectible_code(cell.code):
                self.collected_cells.add(key)
                changed = True
                if kind == "key":
                    self.owned_keys.add(cell.code)
                elif kind == "ammo":
                    self.ammo += 5
                elif (score_value := score_value_for_code(cell.code)) is not None:
                    self.score += score_value
                    popup_tile = score_popup_tile_for_value(score_value)
                    if popup_tile is not None:
                        self.entities.score_popups.append(
                            ScorePopup(float(cell.x * TILE), float(cell.y * TILE - 8), score_value, popup_tile)
                        )
                elif kind == "glasses":
                    self.has_glasses = True
            elif is_door_code(cell.code) and door_unlocked_by(cell.code) in self.owned_keys:
                self.opened_doors.add(key)
                self.owned_keys.discard(door_unlocked_by(cell.code))
                changed = True
        if changed:
            self.rebuild_level_image()


    def collect_rip_enemies(self) -> None:
        p = self.player
        left, top = p.x, p.y
        right, bottom = p.x + PLAYER_W - 1, p.y + PLAYER_H - 1
        kept = []
        for enemy in self.entities.enemies:
            if enemy.is_rip and not (right < enemy.x or left > enemy.x + TILE - 1 or bottom < enemy.y or top > enemy.y + TILE - 1):
                self.score += BANK14_RIP_PICKUP_SCORE
                self.spawn_score_popup(enemy.x, enemy.y, BANK14_RIP_PICKUP_SCORE)
                continue
            kept.append(enemy)
        self.entities.enemies = kept

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
            self.hurt_flash = 0.75
            # Placeholder for lives/health until the EXE damage routine is mapped.
            # Give immediate visual/physical feedback without ending the level.
            self.player.jump_anim_timer = 0
            self.player.grounded = False
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
        view_w, view_h = self.viewport_size()
        max_x = max(0, LEVEL_W * TILE - view_w)
        max_y = max(0, LEVEL_H * TILE - view_h)
        x = int(min(max(p.x + PLAYER_W / 2 - view_w / 2, 0), max_x))
        y = int(min(max(p.y + PLAYER_H / 2 - view_h / 2, 0), max_y))
        return x, y

    def draw(self) -> None:
        if self.level_image is None:
            return
        cam_x, cam_y = self.camera()
        view_w, view_h = self.viewport_size()
        frame = self.level_image.crop((cam_x, cam_y, cam_x + view_w, cam_y + view_h)).convert("RGBA")
        draw = ImageDraw.Draw(frame)

        p = self.player
        px = int(p.x - cam_x)
        py = int(p.y - cam_y)
        if self.is_world_map:
            self.draw_world_player(frame, px, py)
            self.draw_world_entrance_numbers(frame, cam_x, cam_y)
        else:
            self.draw_entities(frame, cam_x, cam_y)
            self.draw_player_sprite(frame, px, py)

        scaled_frame = frame.resize((view_w * self.zoom, view_h * self.zoom), Image.Resampling.NEAREST) if self.zoom != 1 else frame
        out_w = max(self.canvas_w, scaled_frame.width)
        hud = Image.new("RGBA", (out_w, HUD_H), (8, 8, 12, 255))
        hd = ImageDraw.Draw(hud)
        mode = "World map" if self.is_world_map else "Platform level"
        status = (
            f"EP {self.episode_number}/3   {mode} {self.level_index}/{self.level_count - 1}   "
            f"View {view_w}x{view_h}@{self.zoom}x   Collision {'on' if self.collision_enabled else 'off'}   "
            f"Score {self.score}   Ammo {self.ammo}   "
            f"Keys {','.join(f'0x{k:02X}' for k in sorted(self.owned_keys)) or '-'}{self.current_world_level_hint()}"
        )
        controls = (
            "Map: arrows/WASD move, Space/Enter opens level. Level: arrows/A-D move, Space jump, Ctrl fire. "
            "+/- or Ctrl+wheel zoom, resize window, PgUp/PgDn level, Q/E episode, M map, R reset"
        )
        hd.text((8, 7), status, fill=(255, 255, 255, 255))
        hd.text((8, 27), controls, fill=(180, 190, 210, 255))
        out = Image.new("RGBA", (out_w, scaled_frame.height + HUD_H), (0, 0, 0, 255))
        out.alpha_composite(scaled_frame, (0, 0))
        out.alpha_composite(hud, (0, scaled_frame.height))

        self.frame_photo = ImageTk.PhotoImage(out)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.frame_photo, anchor="nw")

    def draw_world_player(self, frame: Image.Image, px: int, py: int) -> None:
        self.draw_player_sprite(frame, px, py, offset=(-2, -1))

    def draw_player_sprite(self, frame: Image.Image, px: int, py: int, *, offset: tuple[int, int] = (0, 0)) -> None:
        if self.is_world_map:
            tile_ref = (13, 0)
        else:
            tile_ref = player_tile(
                state=self.player.anim_state,
                walk_counter=self.player.walk_counter,
            )
        tile = self.episode.tiles16.get(*tile_ref)
        if tile:
            frame.alpha_composite(tile, (px + offset[0], py + offset[1]))
            return
        draw = ImageDraw.Draw(frame)
        draw.rectangle([px, py, px + PLAYER_W - 1, py + PLAYER_H - 1], fill=(255, 220, 64, 255), outline=(0, 0, 0, 255))

    def draw_entities(self, frame: Image.Image, cam_x: int, cam_y: int) -> None:
        for platform in self.entities.platforms:
            self.draw_code_sprite(frame, platform.code, int(platform.x - cam_x), int(platform.y - cam_y))
        for enemy in self.entities.enemies:
            if enemy.bank == 14 and enemy.base_tile is not None:
                animated = bank14_guard_tile(enemy.base_tile, direction=enemy.direction, frame_counter=enemy.frame_counter)
            else:
                animated = walker_tile(enemy.code, direction=enemy.direction, anim_time=enemy.anim_time, frame_counter=enemy.frame_counter)
            if animated is not None:
                tile = self.episode.tiles16.get(*animated)
                if tile:
                    frame.alpha_composite(tile, (int(enemy.x - cam_x), int(enemy.y - cam_y)))
                    continue
            self.draw_code_sprite(frame, enemy.code, int(enemy.x - cam_x), int(enemy.y - cam_y))
        draw = ImageDraw.Draw(frame)
        for shot in self.entities.projectiles:
            x = int(shot.x - cam_x)
            y = int(shot.y - cam_y)
            fill = (255, 96, 80, 255) if shot.hostile else (255, 255, 96, 255)
            draw.rectangle([x, y, x + 3, y + 1], fill=fill)
        for popup in self.entities.score_popups:
            tile = self.episode.tiles16.get(10, popup.tile)
            if tile:
                frame.alpha_composite(tile, (int(popup.x - cam_x), int(popup.y - cam_y)))

    def draw_code_sprite(self, frame: Image.Image, code: int, px: int, py: int) -> None:
        from secret_agent_editor.mapping import TILE_MAP

        refs = TILE_MAP.get(code, [])
        for relx, rely, bank, tile_no in refs:
            tile = self.episode.tiles16.get(bank, tile_no)
            if tile:
                frame.alpha_composite(tile, (px + relx * TILE, py + rely * TILE))

    def draw_world_entrance_numbers(self, frame: Image.Image, cam_x: int, cam_y: int) -> None:
        draw = ImageDraw.Draw(frame)
        for x, y, level in self.world_entrances():
            sx = x * TILE - cam_x
            sy = y * TILE - cam_y
            view_w, view_h = self.viewport_size()
            if -16 <= sx < view_w and -16 <= sy < view_h:
                draw.text((sx + 1, sy + 1), str(level), fill=(0, 0, 0, 255))
                draw.text((sx, sy), str(level), fill=(255, 255, 0, 255))


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
