"""HUD and 8x8 UI sprite drawing helpers.

This module intentionally contains only rendering helpers and factual page
mapping for ``SAM?02.GFX``.  Gameplay state stays in ``runtime.OpenAgentApp``;
these methods are mixed in so the large runtime file no longer has to carry the
status-bar/menu text renderer as another 180-line block.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

if TYPE_CHECKING:  # pragma: no cover - only for type checkers/editors
    from .runtime import OpenAgentApp

# The DOS game uses a 320x200 framebuffer.  The status strip is the bottom
# eight pixels, not a modern UI widget below the game view.
STATUS_BAR_H = 8

# 8x8 UI pointer pages from the executable loader.  Camoto exposes these as the
# three headered 2k blocks in SAM?02.GFX; the EXE stores their far pointers
# separately and uses them for different UI families.
UI_TEXT_PAGE_0 = 0  # DS:6E36, menu/table text chars 0x20..0x48
UI_TEXT_PAGE_1 = 1  # DS:6E3A, menu/table text chars 0x5D..0x75
UI_HUD_PAGE = 2     # DS:6E32, status bar digits/icons

HUD_AMMO_MAX = 0x63

# Legacy fallback glyphs used only if SAM?02.GFX is missing.  The real game
# HUD/menu font and icons are 8x8 masked cells in SAM?02.GFX, not normal 16x16
# tiles.  Keep this intentionally tiny and visibly fallback-only.
HUD_GLYPHS: dict[str, tuple[str, ...]] = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "A": ("010", "101", "111", "101", "101"),
    ":": ("0", "1", "0", "1", "0"),
}


class HUDMixin:
    """Drawing methods used by ``OpenAgentApp``.

    The mixin expects the app to expose ``episode``, ``score``, ``ammo``,
    ``has_floppy_disk``, ``has_glasses``, ``owned_keys``, ``lives`` and
    ``player_dead_timer``.  It deliberately does not mutate gameplay state.
    """

    def hud_tile(self: "OpenAgentApp", bank: int, tile: int) -> Image.Image | None:
        tiles8 = getattr(self.episode, "tiles8", None)
        if tiles8 is None:
            return None
        return tiles8.get(bank, tile)

    def draw_hud_cell(self: "OpenAgentApp", frame: Image.Image, x: int, y: int, bank: int, tile: int) -> int:
        cell = self.hud_tile(bank, tile)
        if cell is None:
            return 8
        frame.alpha_composite(cell, (x, y))
        return 8

    def draw_hud_glyph(
        self: "OpenAgentApp",
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        ch: str,
        fill: tuple[int, int, int, int],
    ) -> int:
        # Fallback only; normal path uses SAM?02.GFX cells below.
        glyph = HUD_GLYPHS.get(ch.upper())
        if glyph is None:
            return 4
        for yy, row in enumerate(glyph):
            for xx, bit in enumerate(row):
                if bit == "1":
                    draw.point((x + xx, y + yy), fill=fill)
        return len(glyph[0]) + 1

    def draw_hud_text(
        self: "OpenAgentApp",
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        text: str,
        fill: tuple[int, int, int, int],
    ) -> int:
        for ch in text:
            x += self.draw_hud_glyph(draw, x, y, ch, fill)
        return x

    def draw_hud_digit_string(
        self: "OpenAgentApp",
        frame: Image.Image,
        x: int,
        y: int,
        text: str,
        *,
        bank: int = UI_HUD_PAGE,
        digit_base: int = 0,
    ) -> int:
        # HUD/status digits are drawn from DS:6E32.  The ASM formula is
        #   DS:6E32 + (ascii_digit - 0x2F) * 0x28 - 0x25
        # For '0' this lands at DS:6E32 + 3, i.e. the first 8x8 sprite after
        # the header.  Therefore tile 0 == '0', tile 1 == '1', etc.
        for ch in text:
            if ch.isdigit():
                x += self.draw_hud_cell(frame, x, y, bank, digit_base + ord(ch) - ord("0"))
            elif ch == ":":
                x += self.draw_hud_cell(frame, x, y, bank, digit_base + 10)
            else:
                x += 8
        return x

    def ui_text_tile_ref(self: "OpenAgentApp", ch: str) -> tuple[int, int] | None:
        """Map a menu/table text character to the SAM?02.GFX 8x8 sprite page.

        This mirrors the text renderer around SAM1:0x18822.  It does not yet
        cover the later large special-glyph branches at 0x18960+, but it covers
        the two normal 8x8 text pages used by menu/table text:

        * DS:6E36 for ASCII 0x20..0x48, tile = ch - 0x20 + 9
        * DS:6E3A for ASCII 0x5D..0x75, tile = ch - 0x5D + 20

        HUD/status text is separate and uses DS:6E32 through
        draw_hud_digit_string().
        """
        if not ch:
            return None
        code = ord(ch)
        if code == 0x20:
            return None
        if 0x20 <= code <= 0x48:
            return (UI_TEXT_PAGE_0, code - 0x20 + 9)
        if 0x5D <= code < 0x76:
            return (UI_TEXT_PAGE_1, code - 0x5D + 20)
        return None

    def draw_ui_text_8x8(self: "OpenAgentApp", frame: Image.Image, x: int, y: int, text: str) -> int:
        """Draw text using the game's 8x8 menu/table sprite pages when possible."""
        if getattr(self.episode, "tiles8", None) is None:
            draw = ImageDraw.Draw(frame)
            return self.draw_hud_text(draw, x, y, text, (230, 230, 230, 255))
        start_x = x
        for ch in text:
            ref = self.ui_text_tile_ref(ch)
            if ref is not None and self.hud_tile(*ref) is not None:
                frame.alpha_composite(self.hud_tile(*ref), (x, y))
            # Unknown chars still advance exactly one cell; this keeps table
            # layouts stable until the remaining special branches are decoded.
            x += 8
        return x - start_x

    def draw_hud_icon(self: "OpenAgentApp", frame: Image.Image, x: int, y: int, kind: str) -> int:
        # Status-bar icons are addressed as byte offsets from DS:6E32 in the
        # ASM.  Since each headered SAM?02.GFX sprite is 0x28 bytes and the data
        # begins at offset 3, these offsets map directly to sprite IDs in the
        # HUD page.
        icon_tiles = {
            "life": (UI_HUD_PAGE, 11),
            "ammo": (UI_HUD_PAGE, 12),
            "speed": (UI_HUD_PAGE, 13),
            "disk": (UI_HUD_PAGE, 17),
            "key": (UI_HUD_PAGE, 18),
            "glasses": (UI_HUD_PAGE, 21),
        }
        bank_tile = icon_tiles.get(kind)
        if bank_tile is not None and self.hud_tile(*bank_tile) is not None:
            return self.draw_hud_cell(frame, x, y, *bank_tile)
        # Last-resort old fallback for incomplete data sets.
        draw = ImageDraw.Draw(frame)
        return self.draw_hud_icon_fallback(draw, x, y, kind)

    def draw_hud_icon_fallback(self: "OpenAgentApp", draw: ImageDraw.ImageDraw, x: int, y: int, kind: str) -> int:
        if kind == "life":
            fill = (220, 80, 90, 255)
            pts = [(1, 1), (2, 0), (3, 1), (4, 0), (5, 1), (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (2, 4), (3, 4), (4, 4), (3, 5)]
        elif kind == "key":
            fill = (230, 210, 80, 255)
            pts = [(0, 2), (1, 1), (2, 1), (3, 2), (2, 3), (1, 3), (3, 2), (4, 2), (5, 2), (5, 3), (6, 2)]
        elif kind == "disk":
            fill = (120, 140, 255, 255)
            pts = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (0, 1), (4, 1), (0, 2), (1, 2), (2, 2), (4, 2), (0, 3), (4, 3), (0, 4), (1, 4), (2, 4), (3, 4), (4, 4)]
        elif kind == "glasses":
            fill = (120, 230, 220, 255)
            pts = [(0, 2), (1, 1), (2, 1), (3, 2), (4, 2), (5, 1), (6, 1), (7, 2), (1, 3), (2, 3), (5, 3), (6, 3), (3, 2), (4, 2)]
        else:
            fill = (170, 170, 170, 255)
            pts = [(0, 0), (1, 0), (0, 1), (1, 1)]
        for px, py in pts:
            draw.point((x + px, y + py), fill=fill)
        return 8

    def draw_status_bar(self: "OpenAgentApp", frame: Image.Image, view_w: int, screen_h: int) -> None:
        # Original HUD is exactly the bottom 8 pixels of the 320x200 framebuffer.
        # Its art comes from SAM?02.GFX (8x8 masked cells).  Earlier passes used
        # guessed PIL/text masks; this uses the real decoded game cells.
        bar_y = max(0, screen_h - STATUS_BAR_H)
        draw = ImageDraw.Draw(frame)
        draw.rectangle([0, bar_y, view_w, screen_h], fill=(0, 0, 0, 255))
        y = bar_y
        if getattr(self.episode, "tiles8", None) is not None:
            self.draw_hud_digit_string(frame, 0, y, f"{self.score % 1000000:06d}")
            # ASM status routine places ammo digits directly in slots 0x0e and
            # 0x0f; it does not draw an invented "A:" label.
            self.draw_hud_digit_string(frame, 0x70, y, f"{max(0, min(HUD_AMMO_MAX, self.ammo)):02d}")
            x = 0xD8
            if self.has_floppy_disk:
                x += self.draw_hud_icon(frame, x, y, "disk")
            if self.has_glasses:
                x += self.draw_hud_icon(frame, x, y, "glasses")
            for _key in sorted(self.owned_keys):
                x += self.draw_hud_icon(frame, x, y, "key")
            life_x = 0x100
            for _ in range(max(0, self.lives)):
                life_x += self.draw_hud_icon(frame, life_x, y, "life")
            if self.player_dead_timer > 0:
                self.draw_hud_digit_string(frame, view_w - 16, y, "00")
            return

        # Fallback for stripped data sets without SAM?02.GFX.
        y += 1
        self.draw_hud_text(draw, 0, y, f"{self.score % 1000000:06d}", (120, 230, 160, 255))
        self.draw_hud_text(draw, 96, y, f"A:{max(0, min(HUD_AMMO_MAX, self.ammo)):02d}", (230, 170, 185, 255))
        x = 194
        if self.has_floppy_disk:
            x += self.draw_hud_icon_fallback(draw, x, y, "disk")
        if self.has_glasses:
            x += self.draw_hud_icon_fallback(draw, x, y, "glasses")
        for _key in sorted(self.owned_keys):
            x += self.draw_hud_icon_fallback(draw, x, y, "key")
        life_x = max(120, min(view_w - 8 * max(0, self.lives), 244))
        for _ in range(max(0, self.lives)):
            life_x += self.draw_hud_icon_fallback(draw, life_x, y, "life")
        if self.player_dead_timer > 0:
            self.draw_hud_text(draw, view_w - 18, y, "00", (230, 80, 80, 255))
