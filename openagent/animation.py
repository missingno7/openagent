from __future__ import annotations

from dataclasses import dataclass

# Small renderer-side animation model recovered from the player/actor pass.
# It intentionally keeps DOS EXE state ids in the names, but maps them to the
# tile ranges currently decoded from SAM?01.GFX.

# Player sprites are selected by the EXE state word DS:3500 plus the walking
# counter DS:34F6/5 for states 0x01 and 0x05.  The first prototype used that
# formula for every state, which made 0x0F/0x10 land on the death-looking tiles
# in the decoded bank.  The masked player bank is easier to reason about as a
# mixed table:
#   0..3  walk right
#   4..7  walk left
#   9/10  fire right/left
#   12/13 jump right/left
#   14/15 death
# The non-walking states below therefore use explicit EXE-state -> decoded-tile
# mappings recovered by comparing the draw routine with the decoded bank.
PLAYER_BANK = 13
PLAYER_STATE_WALK_RIGHT = 0x01
PLAYER_STATE_WALK_LEFT = 0x05
PLAYER_STATE_IDLE_RIGHT = 0x09
PLAYER_STATE_IDLE_LEFT = 0x0A
PLAYER_STATE_ALT_RIGHT = 0x0B
PLAYER_STATE_ALT_LEFT = 0x0C
PLAYER_STATE_SHOOT_RIGHT = 0x0B
PLAYER_STATE_SHOOT_LEFT = 0x0C
# These two states are used by the EXE when the player is moving while the
# shot/airborne flag is active. They render as the same left/right jump-looking
# frames in the decoded bank and are kept separate from the actual jump toggle.
PLAYER_STATE_AIR_RIGHT = 0x0D
PLAYER_STATE_AIR_LEFT = 0x0E
PLAYER_STATE_JUMP_RIGHT = 0x0F
PLAYER_STATE_JUMP_LEFT = 0x10
# Backwards-compatible names used by runtime imports.
PLAYER_STATE_FIRE_RIGHT = PLAYER_STATE_SHOOT_RIGHT
PLAYER_STATE_FIRE_LEFT = PLAYER_STATE_SHOOT_LEFT
PLAYER_WALK_COUNTER_START = 1
PLAYER_WALK_COUNTER_MAX = 0x13
PLAYER_WALK_COUNTER_STEP = 2  # DS:3506 is initialized to 2
PLAYER_FIRE_HOLD_SECONDS = 10 / 18.2065  # EXE counter 34EA/6EC1 holds the shot state for about 10 DOS ticks

# The EXE actor record uses frame counter ranges 0x01..0x13 and 0x15..0x27.
# The renderer below compresses those ranges down to the visible 4-frame tile
# loops in SAM?01.GFX. These are source-derived from the current map code ->
# bank/tile mapping, not from a hand-drawn replacement sprite.
ACTOR_WALK_FRAME_SECONDS = 0.11

@dataclass(frozen=True)
class WalkerAnimation:
    bank: int
    right_tiles: tuple[int, ...]
    left_tiles: tuple[int, ...]


WALKER_ANIMATIONS: dict[int, WalkerAnimation] = {
    # 0x65 maps to bank 2 tile 16 and the adjacent tiles form the two direction
    # walking loops: 16..19 and 20..23.
    0x65: WalkerAnimation(2, (16, 17, 18, 19), (20, 21, 22, 23)),
    # 0x75/0x76 are the same 8-frame enemy/object family with different map
    # start frames. Treat both as horizontal walkers once extracted to runtime.
    0x75: WalkerAnimation(2, (8, 9, 10, 11), (12, 13, 14, 15)),
    0x76: WalkerAnimation(2, (8, 9, 10, 11), (12, 13, 14, 15)),
    # 0x6E maps to object id 0x0085 / bank 2 tile 32.  The EXE special actor
    # table treats it as one 4-frame actor family; bank 2 tiles 36..39 are a
    # different blue enemy family, not the left-facing half of 0x6E.  Use the
    # same four frames and mirror the tile in the renderer for left motion.
    0x6E: WalkerAnimation(2, (32, 33, 34, 35), (32, 33, 34, 35)),
    # raw 0x7F -> object id 0x0261 -> bank 5 tile 8 family; behaviour state 6,
    # step 2 px/tick, timer period 2.  It is another small 4-frame walker.
    0x7F: WalkerAnimation(5, (8, 9, 10, 11), (8, 9, 10, 11)),
    # raw 0x5F -> bank 4 shark swimmer.  The decoded bank is directional,
    # not mirrored: 46/47 swim right, 44/45 swim left.
    0x5F: WalkerAnimation(4, (46, 47), (44, 45)),
    # raw 0xAE -> object id 0x0353, bank 0 composite.  TILE_MAP shows the
    # standing object as two side-by-side tiles (0,4).  The surrounding bank-0
    # tiles are the animation phases in groups of four.
    0xAE: WalkerAnimation(0, (0, 1, 2, 3), (0, 1, 2, 3)),
    # raw 0x24 -> bank 2 two-high helmet enemy.  Base top/bottom refs are
    # bank2 40 and 44; use 40..43 / 44..47 as synchronized lower-body frames.
    0x24: WalkerAnimation(2, (40, 41, 42, 43), (40, 41, 42, 43)),
    # Additional decoded special actors from the same table.
    0x56: WalkerAnimation(12, (0, 1, 2, 3), (0, 1, 2, 3)),
    0x58: WalkerAnimation(12, (31, 32, 33, 34), (31, 32, 33, 34)),
    # raw 0x63 -> object id 0x0345 / state 0x21.  The visible bank-12
    # family is 36..43: 36..39 for one horizontal direction, 40..43 for the other.
    0x63: WalkerAnimation(12, (36, 37, 38, 39), (40, 41, 42, 43)),
}


PLAYER_EXPLICIT_TILES: dict[int, int] = {
    # State 0x09 is the right-facing idle/standing frame in the EXE state table.
    PLAYER_STATE_IDLE_RIGHT: 8,
    # The decoded atlas does not have a separate obvious left idle after the
    # right idle; using the first left-walk frame avoids showing the firing frame
    # while standing still to the left.
    PLAYER_STATE_IDLE_LEFT: 4,
    # EXE firing states are 0x0B/0x0C.  The render routine computes
    #     sprite_index = DS:3500 + (DS:34F6 / 5)
    # and the decoded atlas is zero-based after the bank pointer adjustment.
    # With DS:34F6 reset to 1 for non-walking states this gives bank-13
    # tiles 10 and 11 for shooting.  Earlier passes incorrectly subtracted one
    # again and displayed 9/10.
    PLAYER_STATE_SHOOT_RIGHT: 10,
    PLAYER_STATE_SHOOT_LEFT: 11,
    # 0x0D/0x0E are not shooting frames in the decoded bank; they line up with
    # the right/left air pose. Keep them off the death frames.
    PLAYER_STATE_AIR_RIGHT: 12,
    PLAYER_STATE_AIR_LEFT: 13,
    # 0x0F/0x10 are alternated by the jump routine, but both directions should
    # still resolve only to the two real jump/air tiles, never death 15/16.
    PLAYER_STATE_JUMP_RIGHT: 12,
    PLAYER_STATE_JUMP_LEFT: 13,
}


def exe_player_state_tile(state: int, walk_counter: int = PLAYER_WALK_COUNTER_START) -> tuple[int, int]:
    """Return the decoded sprite for the EXE DS:3500/DS:34F6 state."""
    if state in (PLAYER_STATE_WALK_RIGHT, PLAYER_STATE_WALK_LEFT):
        frame_add = max(0, int(walk_counter) // 5)
        tile_no = max(0, state + frame_add - 1)
    else:
        tile_no = PLAYER_EXPLICIT_TILES.get(state, max(0, state - 1))
    return (PLAYER_BANK, tile_no)


def player_tile(*, state: int, walk_counter: int = PLAYER_WALK_COUNTER_START) -> tuple[int, int]:
    return exe_player_state_tile(state, walk_counter)


def actor_walk_counter_next(counter: int, *, direction: int) -> int:
    # EXE actor records keep DS:34D6 in two ranges: 0x01..0x13 and 0x15..0x27.
    start, end = (0x15, 0x27) if direction < 0 else (0x01, 0x13)
    if counter < start or counter > end:
        return start
    counter += 1
    return start if counter > end else counter


def walker_tile(code: int, *, direction: int, anim_time: float = 0.0, frame_counter: int | None = None) -> tuple[int, int] | None:
    model = WALKER_ANIMATIONS.get(code)
    if model is None:
        return None
    frames = model.left_tiles if direction < 0 else model.right_tiles
    if frame_counter is None:
        index = int(anim_time / ACTOR_WALK_FRAME_SECONDS) % len(frames)
    else:
        start = 0x15 if direction < 0 else 0x01
        index = max(0, (frame_counter - start) // 5) % len(frames)
    return (model.bank, frames[index])


def bank14_guard_tile(base_tile: int, *, direction: int, frame_counter: int | None = None) -> tuple[int, int]:
    """Return bank-14 guard walking frame.

    Bank 14 is laid out in 8-tile guard strength blocks.  In each block,
    tiles base+0..base+3 are one facing direction and base+4..base+7 are the
    other.  The same actor frame-counter compression used by the normal walkers
    gives a 4-frame loop.
    """
    if base_tile == 40:
        return (14, 40)
    frames = tuple(range(base_tile + (4 if direction < 0 else 0), base_tile + (8 if direction < 0 else 4)))
    if frame_counter is None:
        index = 0
    else:
        start = 0x15 if direction < 0 else 0x01
        index = max(0, (frame_counter - start) // 5) % len(frames)
    return (14, frames[index])


def satellite_tile(frame_index: int) -> tuple[int, int]:
    return (10, max(0, min(3, frame_index)))

def actor_frame_index(frame_counter: int) -> int:
    return max(0, min(3, (max(1, frame_counter) - 1) // 5))

def multi_tile_actor_refs(code: int, direction: int, frame_counter: int) -> tuple[tuple[int, int, int, int], ...] | None:
    """Return relx,rely,bank,tile refs for multi-cell EXE actors.

    These are the first pass through the special actor table entries that were
    already extracted but not rendered as runtime actors.  The key point is that
    the raw map marker is skipped from the static layer and the visible sprite
    is drawn from the actor object/frame state.
    """
    frame = actor_frame_index(frame_counter)
    if code == 0xAE:
        # Bank-0 two-wide creature.  When walking right the EXE draws the pair
        # as (0,4), (1,5), (2,6), (3,7).  Facing left mirrors the whole
        # two-tile composite, so the tile order must be swapped before the
        # renderer flips each 16x16 cel; otherwise the head/body halves are
        # visibly reversed.
        if direction < 0:
            return ((-1, 0, 0, 4 + frame), (0, 0, 0, frame))
        return ((-1, 0, 0, frame), (0, 0, 0, 4 + frame))
    if code == 0x24:
        # Bank-2 helmet enemy is two tiles high.  Upper and lower halves animate
        # together for now; the EXE state has room for the helmet opening branch
        # and is documented as the next target.
        return ((0, -1, 2, 40 + frame), (0, 0, 2, 44 + frame))
    if code == 0x56:
        return ((0, -1, 12, 0 + frame), (0, 0, 12, 4 + frame))
    if code == 0x58:
        return ((0, -1, 12, 31 + frame), (0, 0, 12, 35 + frame))
    if code == 0x63:
        # Ceiling laser crawler is a one-tile actor using bank12 36..43.
        # It is handled by walker_tile(); do not draw it as a separate
        # multi-tile composite.
        return None
    return None
