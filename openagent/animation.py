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
# These two states are used by the ordinary DS:6EC1 mission jump. They render
# as the same left/right air-looking frames in the decoded bank.
PLAYER_STATE_AIR_RIGHT = 0x0D
PLAYER_STATE_AIR_LEFT = 0x0E
# These are alternated by the separate DS:69F5/DS:69F6 bounce/death-style path.
PLAYER_STATE_JUMP_RIGHT = 0x0F
PLAYER_STATE_JUMP_LEFT = 0x10
PLAYER_DEATH_TILES = (14, 15)
# Backwards-compatible names used by runtime imports.
PLAYER_STATE_FIRE_RIGHT = PLAYER_STATE_SHOOT_RIGHT
PLAYER_STATE_FIRE_LEFT = PLAYER_STATE_SHOOT_LEFT
PLAYER_WALK_COUNTER_START = 1
PLAYER_WALK_COUNTER_MAX = 0x13
PLAYER_WALK_COUNTER_STEP = 2  # DS:3506 is initialized to 2
PLAYER_FIRE_HOLD_SECONDS = 10 / 18.2065  # EXE counter 34EA/6EC1 holds the shot state for about 10 DOS ticks


# Raw 0x77 teleporter visuals.  The map token writes runtime visuals 0x00B3
# (upper solid cell) and 0x00B7 (lower pad).  The draw path treats the bank-10
# sprite ids as one-based, while the decoded atlas is zero-based.
TELEPORTER_BANK = 10
TELEPORTER_TOP_TILES = (28, 29)
TELEPORTER_PAD_TILE = 32
TELEPORT_WARP_TILES = (36, 37, 38, 39)


def teleporter_top_tile(anim_ticks: int) -> tuple[int, int]:
    """Return the animated upper cel for raw 0x77.

    The static runtime visual is 0x00B3; in the EXE draw table it is the
    bank-10 29/30 one-based pair, which is decoded as zero-based tiles 28/29.
    Use the same small fixed-tick cadence used by other cA redraw objects so
    the idle animation is independent of render FPS.
    """
    return (TELEPORTER_BANK, TELEPORTER_TOP_TILES[(max(0, anim_ticks) // 5) & 1])


def teleporter_pad_tile() -> tuple[int, int]:
    return (TELEPORTER_BANK, TELEPORTER_PAD_TILE)


def teleport_warp_tile(timer_ticks: int) -> tuple[int, int]:
    """Return the bank-10 teleport effect cel for DS:69E2.

    SAM1:0x21E4..0x2254 draws over the player while DS:69E0 is active.
    For positive DS:69E2 it computes one-based `0x28 - (timer / 5)`; for the
    post-warp negative half it computes one-based `0x28 + (timer / 5)`.  8086
    signed division truncates toward zero, matching Python int(a / b).
    The decoded atlas is zero-based, hence the final `- 1`.
    """
    q = int(timer_ticks / 5)
    one_based = 0x28 - q if timer_ticks >= 0 else 0x28 + q
    tile = max(TELEPORT_WARP_TILES[0], min(TELEPORT_WARP_TILES[-1], one_based - 1))
    return (TELEPORTER_BANK, tile)

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
    # 0x6E maps to object id 0x0085 / bank 2 tile 32.  Its state 0x26 later
    # spawns a separate object 0x89 lightning actor that uses bank 2 tiles
    # 36..39 below it; those are not the left-facing half of the flyer.
    0x6E: WalkerAnimation(2, (32, 33, 34, 35), (32, 33, 34, 35)),
    # raw 0x7F -> object id 0x0261 -> bank 5 tile 8 family; behaviour state 6,
    # step 2 px/tick, timer period 2.  It is another small 4-frame walker.
    0x7F: WalkerAnimation(5, (8, 9, 10, 11), (8, 9, 10, 11)),
    # raw 0x5F -> bank 4 shark swimmer.  The decoded bank is directional,
    # not mirrored: 46/47 swim right, 44/45 swim left.
    0x5F: WalkerAnimation(4, (46, 47), (44, 45)),
    # raw 0x6D is the bank-3 fire walker.  It is a contact hazard that
    # patrols like the small walkers but is not in the projectile damage set.
    0x6D: WalkerAnimation(3, (44, 45, 46, 47), (44, 45, 46, 47)),
    # raw 0xAE -> object id 0x0353, bank 0 composite.  TILE_MAP shows the
    # standing object as two side-by-side tiles (0,4).  The surrounding bank-0
    # tiles are the animation phases in groups of four.
    0xAE: WalkerAnimation(0, (0, 1, 2, 3), (0, 1, 2, 3)),
    # raw 0x24 -> bank 2 two-high helmet enemy.  Base top/bottom refs are
    # bank2 40 and 44; use 40..43 / 44..47 as synchronized lower-body frames.
    0x24: WalkerAnimation(2, (40, 41, 42, 43), (40, 41, 42, 43)),
    # Additional decoded special actors from the same table.
    0x56: WalkerAnimation(12, (0, 1, 2, 3), (0, 1, 2, 3)),
    # Raw 0x58 / state 0x1F is a two-high bank-12 robot/shooter.  It does
    # not use a mirrored single loop: the EXE keeps left frames in DS:34D6
    # 0x01..0x13 and right frames in 0x3D..0x4F, which map to separate atlas
    # ranges below.  multi_tile_actor_refs() draws the real composite cels.
    0x58: WalkerAnimation(12, (28, 29, 30, 31), (16, 17, 18, 19)),
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
    # 0x0D/0x0E line up with the ordinary right/left air pose.
    PLAYER_STATE_AIR_RIGHT: 12,
    PLAYER_STATE_AIR_LEFT: 13,
    # 0x0F/0x10 are alternated by the DS:69F5 path, but should still resolve
    # only to the two air-looking tiles here, never death 15/16.
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



def state27_walk_counter_next(counter: int, *, direction: int, walking_phase: bool) -> int:
    """Advance raw 0x24 / state 0x27 frame counter using its EXE ranges.

    Unlike the generic actors, state 0x27 uses 0x01..0x13 for left-facing
    frames and 0xC9..0xDB for right-facing frames. During the stationary/open
    phase the EXE clamps at the end of the range instead of wrapping; while
    DS:34DE is non-zero it wraps back to the start.
    """
    start, end = (0xC9, 0xDB) if direction > 0 else (0x01, 0x13)
    if counter < start or counter > end:
        return start
    counter += 1
    if counter > end:
        return start if walking_phase else end
    return counter


def state27_frame_index(frame_counter: int, *, direction: int) -> int:
    start = 0xC9 if direction > 0 else 0x01
    return max(0, min(3, (max(start, frame_counter) - start) // 5))


def state27_actor_refs(direction: int, frame_counter: int, *, walking_phase: bool) -> tuple[tuple[int, int, int, int], ...]:
    """Return the raw 0x24 two-high helmet actor cel refs.

    The lower/body part walks through bank-2 tiles 44..47.  The upper helmet
    part is not synchronized while walking: in the original game the visor stays
    closed during DS:34DE walking time and only uses the 40..43 opening frames
    during the stopped/vulnerable phase.
    """
    frame = state27_frame_index(frame_counter, direction=direction)
    top = 40 if walking_phase else 40 + frame
    return ((0, -1, 2, top), (0, 0, 2, 44 + frame))


def state1f_walk_counter_start(direction: int) -> int:
    """Return the state-0x1F / raw-0x58 DS:34D6 start value.

    SAM1:0x12181..0x121A6 initializes DS:34D6 to 0x3D for right-facing
    direction +1 and to 0x01 for left-facing direction -1.  The update branch
    at SAM1:0x936B..0x93BC wraps those ranges while walking and
    SAM1:0x92F2..0x9343 clamps them while stopped/open.
    """
    return 0x3D if direction > 0 else 0x01


def state1f_walk_counter_next(counter: int, *, direction: int, walking_phase: bool) -> int:
    """Advance raw 0x58 / state 0x1F frame counter using EXE ranges."""
    start, end = (0x3D, 0x4F) if direction > 0 else (0x01, 0x13)
    if counter < start or counter > end:
        return start
    counter += 1
    if counter > end:
        return start if walking_phase else end
    return counter


def state1f_frame_index(frame_counter: int, *, direction: int) -> int:
    start = 0x3D if direction > 0 else 0x01
    return max(0, min(3, (max(start, frame_counter) - start) // 5))


def state1f_is_vulnerable(direction: int, frame_counter: int, *, walking_phase: bool) -> bool:
    """Return whether raw 0x58/state 0x1F exposes its damageable top.

    The lower body walks through all four cels, but the top cover remains
    closed while DS:34DE is non-zero.  The object-specific hit branch only
    allows damage once the stopped/open phase has clamped to its final frame:
    bank12 tile 19 when facing left, tile 31 when facing right.
    """
    return (not walking_phase) and state1f_frame_index(frame_counter, direction=direction) >= 3


def state1f_actor_refs(direction: int, frame_counter: int, *, walking_phase: bool = False) -> tuple[tuple[int, int, int, int], ...]:
    """Return the raw 0x58 two-high bank-12 cel refs.

    ASM-backed atlas mapping: left-facing top 16..19 / bottom 20..23;
    right-facing top 28..31 / bottom 32..35.  While walking, the top tile is
    held closed (16 or 28); only the bottom half cycles.  During the stopped
    firing phase the top extends through 17..19 / 29..31 and becomes
    vulnerable only on the final cel.
    """
    frame = state1f_frame_index(frame_counter, direction=direction)
    if direction > 0:
        top = 28 if walking_phase else 28 + frame
        return ((0, -1, 12, top), (0, 0, 12, 32 + frame))
    top = 16 if walking_phase else 16 + frame
    return ((0, -1, 12, top), (0, 0, 12, 20 + frame))


def state2a_dog_counter_next(counter: int, *, direction: int) -> int:
    """Advance raw 0xAE / state 0x2A frame counter.

    ASM SAM1:0x889C..0x88E6 uses two non-generic ranges: right-facing
    DS:34D6 = 0x01..0x13 and left-facing DS:34D6 = 0x29..0x3B.
    The older generic 0x15..0x27 left range made the port render only one
    apparent frame while moving left.
    """
    start, end = (0x29, 0x3B) if direction < 0 else (0x01, 0x13)
    if counter < start or counter > end:
        return start
    counter += 1
    return start if counter > end else counter


def state2a_dog_frame_index(frame_counter: int, *, direction: int) -> int:
    start = 0x29 if direction < 0 else 0x01
    return max(0, min(3, (max(start, frame_counter) - start) // 5))

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
        # Bank-0 two-wide dog/creature.  State 0x2A does not use the generic
        # actor left range; left-facing frames are DS:34D6 0x29..0x3B.
        frame = state2a_dog_frame_index(frame_counter, direction=direction)
        if direction < 0:
            return ((-1, 0, 0, 4 + frame), (0, 0, 0, frame))
        return ((-1, 0, 0, frame), (0, 0, 0, 4 + frame))
    if code == 0x24:
        # Callers that do not know the phase get the conservative closed-helmet
        # walking rendering.  Runtime passes the actual phase through
        # state27_actor_refs() so the helmet only opens while stopped.
        return state27_actor_refs(direction, frame_counter, walking_phase=True)
    if code == 0x56:
        return ((0, -1, 12, 0 + frame), (0, 0, 12, 4 + frame))
    if code == 0x58:
        # Unknown callers should prefer the safe/closed walking top.  Runtime
        # passes the live DS:34DE phase when it renders the actual actor slot.
        return state1f_actor_refs(direction, frame_counter, walking_phase=True)
    if code == 0x63:
        # Ceiling laser crawler is a one-tile actor using bank12 36..43.
        # It is handled by walker_tile(); do not draw it as a separate
        # multi-tile composite.
        return None
    return None


def state2b_tile(frame_counter: int) -> tuple[int, int]:
    # raw 0x40 / object 0x0131 animates only the upper cel through bank9 4..7.
    # DS:34D6 still runs 1..0x13, so compress each five-count range to one
    # visible cel instead of cycling through the whole decoded bank row.
    frame = max(1, min(0x13, frame_counter))
    return (9, 4 + ((frame - 1) // 5) % 4)


def state2b_actor_refs(frame_counter: int) -> tuple[tuple[int, int, int, int], ...]:
    """Return the visible composite for raw 0x40/state 0x2B.

    The EXE treats object 0x0131 as a two-cell decoration/trap with a static
    lower body and the animated top above the map origin.  The animated part is
    the bank9 4..7 family; tile 8 is the stable lower base seen under it.
    """
    bank, top_tile = state2b_tile(frame_counter)
    return ((0, -1, bank, top_tile), (0, 0, bank, 8))

def state2c_tile(code: int, frame_counter: int) -> tuple[int, int]:
    # State 0x2C advances DS:34D6, but the decoded sprite family is not a
    # 19-tile run for every object.  Raw 0xD4/object 0x0135 is the small
    # two-frame bank-9 flame/steam decoration at tiles 8..9; cycling the whole
    # bank-9 row incorrectly showed control-room/armory graphics.  Raw 0x78 /
    # object 0x0103 remains the bank-15 8..11 contact-hazard family.
    frame = max(1, frame_counter)
    if code == 0xD4:
        return (9, 8 + ((frame - 1) // 5) % 2)
    if code == 0x78:
        return (15, 8 + ((frame - 1) // 5) % 4)
    return (9, 8)

def state17_landmine_tile(object_id: int, frame_counter: int) -> tuple[int, int]:
    frame = max(1, frame_counter)
    if object_id == 0x0271:
        # Triggered object 0x0271 is drawn by the special branch at
        # SAM1:0x3728..0x378E: floor(DS:34D6 / 3) is added to the object-family
        # base.  Keep the current decoded bank-5 approximation but match the
        # original timing instead of using a made-up four-tick cadence.
        # The object-family ids 0x0271+ map to the same visible explosion
        # cels as projectile impacts in the decoded atlas.  Using bank5 44 here
        # produced a fully black square on several tilesets.
        return (5, (24, 25, 26, 27)[min(3, (frame - 1) // 3)])
    # Idle object 0x0270 is the raw 0x4D mine.  The draw path at
    # SAM1:0x36C2..0x3725 divides DS:34D6 by five, and the state-0x17 update
    # wraps non-triggered mines after DS:34D6 > 9.  That produces a two-cel
    # blink; in the decoded atlas those cels are bank 5 tile 23 and tile 41.
    return (5, (23, 41)[min(1, (frame - 1) // 5)])
