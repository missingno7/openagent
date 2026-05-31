from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TileAnimation:
    frames: tuple[tuple[int, int], ...]
    period_ticks: int
    note: str = ""


# EXE-derived animated runtime draw cases.
#
# Important correction after pass19:
#   BACKGROUND_MAP four-tile groups are not animation frames. Codes 0x35..0x37
#   are static background-variant/light tiles (used for lamps/shading).  The
#   actual observed animated tile path is a special runtime draw branch for
#   visual id 0x01F3 (bank 4 tile 48).  The renderer branch compares the global
#   draw offset/timer at DS:6840 against 0x10 and draws one of two graphics:
#   the normal tile and the paired graphic at bank 4 tile 0.
#
# We key this table by the normal decoded atlas tile reference, because the
# editor/runtime renderer works from bank/tile DrawRefs rather than raw EXE
# planar bitmap pointers.
ANIMATED_TILES: dict[tuple[int, int], TileAnimation] = {
    # Raw 0x23 / object 0x0097 is normally promoted to a runtime actor.
    # The special actor table gives DS:34D8=3 for state 0x20; in-game testing
    # and the object branch agree that this is the visible satellite phase
    # period, not the slower generic walker counter used in pass23.
    (10, 0): TileAnimation(
        frames=((10, 0), (10, 1), (10, 2), (10, 3)),
        period_ticks=3,
        note="EXE special actor state 0x20 / object 0x0097 uses a 3-DOS-tick phase for the bank10 0..3 satellite loop.",
    ),
    (4, 48): TileAnimation(
        frames=((4, 48), (4, 0)),
        period_ticks=4,
        note="EXE special-case for visual id 0x01F3: DS:6840 draw-phase branch alternates bank 4 tile 48 with bank 4 tile 0; runtime uses 4 DOS ticks per phase.",
    ),
}


def animated_tile_ref(bank: int, tile: int, tick: int = 0) -> tuple[int, int]:
    anim = ANIMATED_TILES.get((bank, tile))
    if not anim:
        return bank, tile
    phase = (max(0, tick) // max(1, anim.period_ticks)) % len(anim.frames)
    return anim.frames[phase]


def background_variant_tile_ref(bg_code: int, variant_code: int) -> tuple[int, int] | None:
    """Return the static background-derived tile for map codes 0x35..0x37.

    These codes are *not* animation phases.  They select fixed variants from the
    active level background block.  In game levels they are used as static light
    or shadow/background detail, e.g. lamp glow.
    """
    from .mapping import BACKGROUND_MAP, DEFAULT_BG

    if variant_code not in (0x35, 0x36, 0x37):
        return None
    bank, tile = BACKGROUND_MAP.get(bg_code, DEFAULT_BG)
    return bank, tile + (variant_code - 0x34)
