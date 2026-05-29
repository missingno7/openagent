from __future__ import annotations

import argparse
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

from .entities import LevelEntities, MovingPlatform, extract_level_entities
from .level_model import codes_at, iter_map_cells
from .loader import Campaign, ensure_editor_importable, load_campaign
from .semantics import (
    MISSION_PLAYER_START_CODE,
    WORLD_BLOCKED_CODES,
    WORLD_ENTRANCE_CODES,
    WORLD_PLAYER_CODE,
    is_mission_code_solid,
)

ROOT = Path(__file__).resolve().parents[1]
ensure_editor_importable(ROOT)

from secret_agent_editor.constants import LEVEL_H, LEVEL_W, ROW_BYTES, TILE
from secret_agent_editor.render import SecretAgentRenderer


VIEW_W = 640
VIEW_H = 400
HUD_H = 48
PLAYER_W = 12
PLAYER_H = 15
MOVE_SPEED = 110.0
WORLD_MOVE_SPEED = 72.0
JUMP_SPEED = 250.0
GRAVITY = 620.0
MAX_FALL = 360.0


@dataclass
class Player:
    x: float = 32.0
    y: float = 32.0
    vx: float = 0.0
    vy: float = 0.0
    grounded: bool = False


class OpenAgentApp:
    def __init__(self, campaign: Campaign, *, episode: int = 1, level: int = 0) -> None:
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
        self.level_image: Image.Image | None = None
        self.level_photo: ImageTk.PhotoImage | None = None
        self.frame_photo: ImageTk.PhotoImage | None = None
        self.entities = LevelEntities([], [])
        self.last_tick = time.perf_counter()

        self.root = tk.Tk()
        self.root.title("OpenAgent")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(self.root, width=VIEW_W, height=VIEW_H + HUD_H, highlightthickness=0, bg="black")
        self.canvas.pack()
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

    def on_key_release(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym)

    def change_episode(self, delta: int) -> None:
        self.episode_index = (self.episode_index + delta) % len(self.episode_numbers)
        self.level_index = min(self.level_index, self.level_count - 1)
        self.load_level(reset_player=True)

    def change_level(self, delta: int) -> None:
        self.level_index = (self.level_index + delta) % self.level_count
        self.load_level(reset_player=True)

    def load_level(self, *, reset_player: bool) -> None:
        renderer = SecretAgentRenderer(self.episode)
        self.level_image = renderer.render(
            self.level_index,
            zoom=1,
            show_codes=self.show_codes,
            show_unknown=self.show_unknown,
        )
        self.entities = LevelEntities([], []) if self.is_world_map else extract_level_entities(self.episode.levels[self.level_index])
        if reset_player:
            if self.is_world_map:
                spawn = self.last_world_position or self.find_world_spawn()
                self.player = Player(spawn[0], spawn[1])
            else:
                self.player = Player(*self.find_spawn())
        self.last_tick = time.perf_counter()
        self.draw()

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
        p = self.player
        left = any(k in self.keys for k in ("Left", "a", "A"))
        right = any(k in self.keys for k in ("Right", "d", "D"))
        jump = any(k in self.keys for k in ("space", "Up", "w", "W"))

        p.vx = (right - left) * MOVE_SPEED
        if jump and p.grounded:
            p.vy = -JUMP_SPEED
            p.grounded = False

        p.vy = min(MAX_FALL, p.vy + GRAVITY * dt)
        self.move_axis(p.vx * dt, 0.0)
        self.move_axis(0.0, p.vy * dt)

        max_x = LEVEL_W * TILE - PLAYER_W
        max_y = LEVEL_H * TILE - PLAYER_H
        p.x = min(max(p.x, 0), max_x)
        if p.y > max_y:
            p.y = max_y
            p.vy = 0
            p.grounded = True

    def update_entities(self, dt: float) -> None:
        for platform in self.entities.platforms:
            carry_player = self.platform_below() is platform and self.player.vy >= 0
            old_x = platform.x
            dx = platform.direction * platform.speed * dt
            platform.x += dx
            if self.platform_collides(platform):
                platform.x = old_x
                platform.direction *= -1
            elif carry_player:
                self.player.x += platform.x - old_x

    def move_axis(self, dx: float, dy: float) -> None:
        p = self.player
        if not self.collision_enabled:
            p.x += dx
            p.y += dy
            p.grounded = False
            return

        p.x += dx
        if dx and self.player_collides():
            step = -1 if dx > 0 else 1
            while self.player_collides():
                p.x += step
            p.vx = 0

        p.y += dy
        if dy:
            p.grounded = False
        if dy and (self.player_collides() or (dy > 0 and self.player_on_platform())):
            step = -1 if dy > 0 else 1
            while self.player_collides() or (dy > 0 and self.player_on_platform()):
                p.y += step
            if dy > 0:
                p.grounded = True
                platform = self.platform_below()
                if platform is not None:
                    p.y = platform.y - PLAYER_H
            p.vy = 0

    def player_collides(self) -> bool:
        p = self.player
        left = int(p.x) // TILE
        right = int(p.x + PLAYER_W - 1) // TILE
        top = int(p.y) // TILE
        bottom = int(p.y + PLAYER_H - 1) // TILE
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                if self.cell_solid(x, y):
                    return True
        return False

    def cell_solid(self, x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= LEVEL_W or y >= LEVEL_H:
            return True
        info = self.episode.levels[self.level_index]
        cell_codes = [code for code in codes_at(info, x, y) if code not in (0, 0x20, ord("*"))]
        if not cell_codes:
            return False
        return any(is_mission_code_solid(code) for code in cell_codes)

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
        max_x = max(0, LEVEL_W * TILE - VIEW_W)
        max_y = max(0, LEVEL_H * TILE - VIEW_H)
        x = int(min(max(p.x + PLAYER_W / 2 - VIEW_W / 2, 0), max_x))
        y = int(min(max(p.y + PLAYER_H / 2 - VIEW_H / 2, 0), max_y))
        return x, y

    def draw(self) -> None:
        if self.level_image is None:
            return
        cam_x, cam_y = self.camera()
        frame = self.level_image.crop((cam_x, cam_y, cam_x + VIEW_W, cam_y + VIEW_H)).convert("RGBA")
        draw = ImageDraw.Draw(frame)

        p = self.player
        px = int(p.x - cam_x)
        py = int(p.y - cam_y)
        if self.is_world_map:
            self.draw_world_player(frame, px, py)
            self.draw_world_entrance_numbers(frame, cam_x, cam_y)
        else:
            self.draw_player_sprite(frame, px, py)
            self.draw_entities(frame, cam_x, cam_y)

        hud = Image.new("RGBA", (VIEW_W, HUD_H), (8, 8, 12, 255))
        hd = ImageDraw.Draw(hud)
        mode = "World map" if self.is_world_map else "Platform level"
        status = (
            f"EP {self.episode_number}/3   {mode} {self.level_index}/{self.level_count - 1}   "
            f"Collision {'on' if self.collision_enabled else 'off'}{self.current_world_level_hint()}"
        )
        controls = (
            "Map: arrows/WASD move, Space/Enter opens level. Level: arrows/WASD move, Space jump. "
            "PgUp/PgDn level, Q/E episode, M map, R reset"
        )
        hd.text((8, 7), status, fill=(255, 255, 255, 255))
        hd.text((8, 27), controls, fill=(180, 190, 210, 255))
        out = Image.new("RGBA", (VIEW_W, VIEW_H + HUD_H), (0, 0, 0, 255))
        out.alpha_composite(frame, (0, 0))
        out.alpha_composite(hud, (0, VIEW_H))

        self.frame_photo = ImageTk.PhotoImage(out)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.frame_photo, anchor="nw")

    def draw_world_player(self, frame: Image.Image, px: int, py: int) -> None:
        self.draw_player_sprite(frame, px, py, offset=(-2, -1))

    def draw_player_sprite(self, frame: Image.Image, px: int, py: int, *, offset: tuple[int, int] = (0, 0)) -> None:
        tile = self.episode.tiles16.get(13, 0)
        if tile:
            frame.alpha_composite(tile, (px + offset[0], py + offset[1]))
            return
        draw = ImageDraw.Draw(frame)
        draw.rectangle([px, py, px + PLAYER_W - 1, py + PLAYER_H - 1], fill=(255, 220, 64, 255), outline=(0, 0, 0, 255))

    def draw_entities(self, frame: Image.Image, cam_x: int, cam_y: int) -> None:
        for platform in self.entities.platforms:
            self.draw_code_sprite(frame, platform.code, int(platform.x - cam_x), int(platform.y - cam_y))
        for enemy in self.entities.enemies:
            self.draw_code_sprite(frame, enemy.code, int(enemy.x - cam_x), int(enemy.y - cam_y))

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
            if -16 <= sx < VIEW_W and -16 <= sy < VIEW_H:
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
    args = parser.parse_args(argv)

    campaign = load_campaign(args.source)
    app = OpenAgentApp(campaign, episode=args.episode, level=args.level)
    app.run()
    return 0
