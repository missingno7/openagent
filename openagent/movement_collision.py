from __future__ import annotations

from .animation import (
    PLAYER_STATE_AIR_LEFT,
    PLAYER_STATE_AIR_RIGHT,
    PLAYER_STATE_FIRE_LEFT,
    PLAYER_STATE_FIRE_RIGHT,
    PLAYER_STATE_IDLE_LEFT,
    PLAYER_STATE_IDLE_RIGHT,
    PLAYER_STATE_WALK_LEFT,
    PLAYER_STATE_WALK_RIGHT,
)
from .collision import (
    PLAYER_COLLISION_BOTTOM,
    PLAYER_COLLISION_LEFT,
    PLAYER_COLLISION_RIGHT,
    PLAYER_COLLISION_TOP,
    player_body_probes,
)
from .entities import MovingPlatform, PushableBarrel
from .game_constants import (
    FALL_COUNTER_MAX,
    PLAYER_H,
    PLAYER_VERTICAL_STEP_TABLE,
    PLAYER_W,
)
from .level_model import build_runtime_collision_grid, iter_map_cells
from .semantics import (
    ACTIVE_HIDDEN_PLATFORM_COLLISION_CODE,
    HIDDEN_PLATFORM_CODE,
    LASER_FIELD_CODE,
    door_unlocked_by,
    is_door_code,
    is_dynamic_mission_code,
    is_exit_door_code,
)

from openagent.game_assets.constants import LEVEL_H, LEVEL_W, TILE


class MovementCollisionMixin:
    """Player movement, runtime collision-grid queries and actor solid helpers.

    This mixin owns low-level movement/collision mechanics that were previously
    embedded in ``runtime.py``.  It deliberately has no Tk/rendering imports and
    no top-level loop orchestration; callers provide the current player, level
    info, entity lists and ASM-derived helper methods via ``self``.
    """

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
                        # hard tile collision.  A blocked push enters a short
                        # release/pass-through window; do not synthesize a
                        # horizontal counter-nudge that the decoded branch does
                        # not write to actor_x.
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
                    if self.actor_is_contact_hazard(enemy) and getattr(self, "hurt_flash", 0.0) <= 0:
                        self.hurt_player()
                    return True
            for barrel in self.entities.barrels:
                if barrel is self._ignore_barrel_collision and self._ignore_barrel_collision_ticks > 0:
                    continue
                if self.player_barrel_actor_overlap(barrel):
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
        removed = set(self.dynamic_source_keys())
        removed.update(self.collected_cells)
        removed.update(self.opened_doors)
        removed.update(self.opened_exit_doors)
        if self.laser_field_deactivated:
            removed |= self.laser_field_source_keys()
        return removed

    def dynamic_source_keys(self) -> frozenset[tuple[int, int, int, str]]:
        if self.is_world_map:
            return frozenset()
        if self._dynamic_source_keys_cache is None:
            info = self.episode.levels[self.level_index]
            self._dynamic_source_keys_cache = frozenset(
                self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
                for cell in iter_map_cells(info)
                if is_dynamic_mission_code(cell.code)
            )
        return self._dynamic_source_keys_cache

    def laser_field_visible(self) -> bool:
        # Runtime cA 0x025B is one of the EXE's globally blink-redrawn cells.
        # The exact timer is tied to DS:6840 redraw toggles; 4 DOS ticks gives
        # a close visual cadence in this runtime.
        return (self.anim_ticks // 4) % 2 == 0

    def laser_field_source_keys(self) -> frozenset[tuple[int, int, int, str]]:
        if self.is_world_map:
            return frozenset()
        if self._laser_field_source_keys_cache is None:
            info = self.episode.levels[self.level_index]
            self._laser_field_source_keys_cache = frozenset(
                self.runtime_cell_key(cell.x, cell.y, cell.code, cell.layer)
                for cell in iter_map_cells(info)
                if cell.code == LASER_FIELD_CODE
            )
        return self._laser_field_source_keys_cache

    def runtime_collision_grid(self):
        info = self.episode.levels[self.level_index]
        removed = frozenset(self.removed_runtime_source_keys())
        overrides = {HIDDEN_PLATFORM_CODE: ACTIVE_HIDDEN_PLATFORM_COLLISION_CODE} if self.has_glasses else {}
        cache_key = (self.level_index, self.is_world_map, removed, tuple(sorted(overrides.items())))
        if self._collision_grid_cache_key != cache_key:
            self._collision_grid_cache = build_runtime_collision_grid(info, removed_source_keys=removed, code_collision_overrides=overrides, world_map=self.is_world_map)
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
        """Move a falling raw-0xA7 barrel straight down.

        The raw 0xA7 branch must not reuse the generic full-body AABB test
        while falling.  In the EXE, the falling actor keeps its X coordinate and
        resolves vertical support separately; side wall/body cells do not act as
        side-collisions that can stop the downward motion.  Horizontal pushes
        still use ``barrel_collides()`` through ``try_push_barrel()``; this path
        is only the gravity/landing step.
        """
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
            barrel.y += 1
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

    def platform_carry_contact_asm(self, platform: MovingPlatform) -> bool:
        """Return whether SAM1:0x7FA6..0x8105 would snap/carry the player.

        The moving-platform actor branch compares a narrow 10px horizontal
        rectangle for both actor and player (`actor_x..+9` vs `DS:34EE..+9`)
        and requires the actor top to be below the player origin but no lower
        than the player's `y+0x10` base.  Importantly, this path checks
        `DS:6EC1` but not `DS:69F5`, which is why the original game can catch
        and drag the death animation when the falling death sprite crosses a
        platform top.
        """
        p = self.player
        player_left = float(p.x)
        player_right = player_left + 9.0
        platform_left = float(platform.x)
        platform_right = platform_left + 9.0
        horizontal = not (player_right < platform_left or platform_right < player_left)
        if not horizontal:
            return False
        player_top = float(p.y)
        player_base = player_top + 0x10
        platform_top = float(platform.y)
        return player_base >= platform_top and platform_top > player_top

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

    @staticmethod
    def intervals_overlap_inclusive(a_left: float, a_right: float, b_left: float, b_right: float) -> bool:
        return a_left <= b_right and b_left <= a_right

    def player_barrel_horizontal_overlap(self, barrel: PushableBarrel) -> bool:
        """Return the SAM1:0x83C4 shrunken X overlap for player/raw-0xA7."""
        p = self.player
        return self.intervals_overlap_inclusive(
            p.x + PLAYER_COLLISION_LEFT,
            p.x + PLAYER_COLLISION_RIGHT,
            barrel.x + PLAYER_COLLISION_LEFT,
            barrel.x + PLAYER_COLLISION_RIGHT,
        )

    def player_barrel_actor_overlap(self, barrel: PushableBarrel) -> bool:
        """Match the raw-0xA7 actor/player rectangle test at SAM1:0x83C4..0x848A.

        The EXE does not use the full 16x16 sprites here.  It tests both
        horizontal intervals as x+3..x+12 and vertical intervals as y..y+15,
        then routes the result through the barrel actor-state branch instead of
        the normal static collision helper.
        """
        p = self.player
        return (
            self.player_barrel_horizontal_overlap(barrel)
            and self.intervals_overlap_inclusive(
                p.y + PLAYER_COLLISION_TOP,
                p.y + PLAYER_COLLISION_BOTTOM,
                barrel.y + PLAYER_COLLISION_TOP,
                barrel.y + PLAYER_COLLISION_BOTTOM,
            )
        )

    def player_overlaps_barrel(self, barrel: PushableBarrel) -> bool:
        return self.player_barrel_actor_overlap(barrel)

    def release_barrel_against_wall(self, barrel: PushableBarrel, push_step: int) -> None:
        """Enter the EXE-style raw-0xA7 blocked-push release window.

        The disassembly around SAM1:0x83C4..0x848A checks the player's
        shrunken overlap against object id 0x00A7 and transitions the actor
        instead of treating it as an ordinary solid tile.  The following state
        writes DS:34DA=0x10 and adjusts the actor's vertical transient; no
        decoded instruction writes a horizontal counter-step to actor_x.  The
        Python port therefore flips the displayed direction and temporarily
        ignores player/barrel body collision, but it must not pop the barrel
        sideways away from the wall.
        """
        barrel.direction = -push_step
        self._ignore_barrel_collision = barrel
        self._ignore_barrel_collision_ticks = 0x10

    def barrel_below(self) -> PushableBarrel | None:
        p = self.player
        player_bottom = p.y + PLAYER_H
        for barrel in self.entities.barrels:
            horizontal = self.player_barrel_horizontal_overlap(barrel)
            vertical = barrel.y <= player_bottom <= barrel.y + 4
            if horizontal and vertical:
                return barrel
        return None

    def player_barrel_landing_y(self, prev_bottom: float, new_bottom: float) -> float | None:
        """Return the topmost barrel surface crossed by the falling player."""
        prev_base = prev_bottom + 1
        new_base = new_bottom + 1
        candidates: list[float] = []
        for barrel in self.entities.barrels:
            horizontal = self.player_barrel_horizontal_overlap(barrel)
            vertical = prev_base <= barrel.y <= new_base
            if horizontal and vertical:
                candidates.append(float(barrel.y - PLAYER_H))
        return min(candidates) if candidates else None

    def player_touching_barrel(self) -> PushableBarrel | None:
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
        # A successful horizontal push can move raw 0xA7 off the last support
        # pixel before the barrel actor's gravity state runs.  Mark it
        # unsupported immediately so any same-tick carrier/contact logic does
        # not keep treating the old floor as valid.  The actual fall distance is
        # still resolved by update_barrels_tick()/move_barrel_vertical().
        if self.barrel_landing_y(barrel, barrel.y + TILE, barrel.y + TILE + 1) is None:
            barrel.grounded = False
        return True

    def player_on_platform(self) -> bool:
        return self.platform_below() is not None or self.barrel_below() is not None
