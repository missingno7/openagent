from __future__ import annotations

import tkinter as tk

from .game_constants import MAX_ZOOM, MIN_ZOOM
from .hud import STATUS_BAR_H


class WindowMixin:
    """Tk window, keyboard and top-level navigation helpers.

    This mixin intentionally owns only UI/control flow around the fixed-step
    simulation: event bindings, zoom/window size, episode/level switches, and
    the window title. Gameplay state mutation remains in ``runtime.py`` or the
    dedicated gameplay mixins.
    """

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
        elif key in {"i", "I"}:
            self.cycle_render_interpolation_mode()
        elif key in {"plus", "KP_Add", "equal"}:
            self.change_zoom(1)
        elif key in {"minus", "KP_Subtract"}:
            self.change_zoom(-1)

    def on_key_release(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym)

    def on_canvas_configure(self, event: tk.Event) -> None:
        new_w = max(1, int(event.width))
        new_h = max(1, int(event.height))
        if (new_w, new_h) != (self.canvas_w, self.canvas_h):
            self.canvas_w = new_w
            self.canvas_h = new_h
            self._force_next_draw = True

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
        self.last_world_position = None
        self.world_entry_release_level = None
        self.sound.load_episode(self.campaign, self.episode_number)
        self.load_level(reset_player=True)

    def change_level(self, delta: int) -> None:
        self.level_index = (self.level_index + delta) % self.level_count
        self.load_level(reset_player=True)

    def cycle_render_interpolation_mode(self) -> None:
        if not self.visual_interpolation_enabled:
            self.visual_interpolation_enabled = True
            self.visual_interpolation_smoothing = False
        elif not self.visual_interpolation_smoothing:
            self.visual_interpolation_enabled = True
            self.visual_interpolation_smoothing = True
        else:
            self.visual_interpolation_enabled = False
            self.visual_interpolation_smoothing = False
        self.reset_render_interpolation_state()
        self.update_window_title()
        self.draw()

    def render_interpolation_mode_label(self) -> str:
        if not self.visual_interpolation_enabled:
            return "off"
        return "smooth" if self.visual_interpolation_smoothing else "linear"

    def update_window_title(self) -> None:
        suffix = f" | interpolation: {self.render_interpolation_mode_label()} (I cycles)"
        self.root.title("OpenAgent" + suffix)

