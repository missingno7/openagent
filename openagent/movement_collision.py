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
    BARREL_ACTOR_STEP_PX,
    FALL_COUNTER_MAX,
    PLAYER_H,
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
                        # Do not map a wall-blocked push to the destructive
                        # 0x1389/+score branch.  The original wall case behaves
                        # as a body-pass-through/top-solid barrel until the
                        # player clears through it, then the barrel reappears on
                        # the free side.
                        self.release_barrel_against_wall(barrel, step)
                self.update_wall_release_barrels()
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
        if self.has_active_wall_release_barrel():
            # A wall-released raw 0xA7 is no longer returned by
            # player_touching_barrel() because its body is pass-through.  Keep
            # using the reconstructed pixel path until the release window
            # resolves, otherwise update_wall_release_barrels() is never polled
            # by the normal atomic movement path and the barrel stays stuck at
            # the wall forever.  The underlying ASM actor branch is evaluated
            # once per game tick while state 0x1388 remains active, so this is
            # a control-flow fix rather than a new gameplay state.
            return self.move_axis_pixels(step, 0)
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
                if self.barrel_body_is_pass_through(barrel):
                    continue
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
        kept_barrels: list[PushableBarrel] = []
        for barrel in self.entities.barrels:
            if barrel.is_transient:
                self.update_barrel_1389_transient(barrel)
                if barrel.is_transient:
                    kept_barrels.append(barrel)
                elif barrel is self._ignore_barrel_collision:
                    self._ignore_barrel_collision = None
                    self._ignore_barrel_collision_ticks = 0
                continue

            carry_player = self.barrel_below() is barrel and self.player.grounded
            landing_y = self.barrel_landing_y(barrel, barrel.y + TILE, barrel.y + TILE + 1)
            if landing_y is not None and landing_y >= barrel.y and abs(barrel.y - landing_y) <= 1.0:
                barrel.y = landing_y
                barrel.grounded = True
                barrel.fall_ticks = 0
                barrel.falling_locked = False
                kept_barrels.append(barrel)
                continue
            barrel.grounded = False
            barrel.falling_locked = True
            barrel.fall_ticks = min(FALL_COUNTER_MAX, barrel.fall_ticks + 1)
            # Do not reuse the player DS:34AF gravity table here. The raw
            # 0xA7 branch is an actor record, and the currently decoded actor
            # movement/spawn evidence points at a fixed 4px actor-style step.
            # The exact 0x1388 pushed-off-edge store is still a research gap,
            # so keep this as a small named constant instead of hiding it in
            # the player motion table.
            moved = self.move_barrel_vertical(barrel, BARREL_ACTOR_STEP_PX)
            if carry_player and moved:
                self.player.y += moved
                self.player.grounded = True
            kept_barrels.append(barrel)
        self.entities.barrels = kept_barrels

    def update_barrel_1389_transient(self, barrel: PushableBarrel) -> None:
        """Advance the ASM state-0x1389 raw-barrel transient one actor tick.

        SAM1:0x854A..0x85B8 stores previous/current draw coordinates, subtracts
        two pixels from ``DS:34D0`` with an absolute clamp at 0x10, decrements
        ``DS:34DA``, and only then chooses the cleanup redraw path.  There is no
        decoded write to ``DS:34CE``/actor X in this state, so the port must not
        synthesize a horizontal snap when a wall-blocked push releases.
        """
        barrel.y = max(0x10, barrel.y - 2)
        barrel.grounded = False
        barrel.fall_ticks = 0
        barrel.transient_ticks = max(0, barrel.transient_ticks - 1)
        if barrel.transient_ticks == 0:
            # SAM1:0x85BB marks DS:34EB=1 after the timer expires.  In the
            # object-list runtime that means removing the actor from the live
            # pushable-barrel list after its final cleanup tick.
            barrel.behavior_state = 0


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
                barrel.falling_locked = False
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
            if other is barrel or self.barrel_top_is_pass_through(other):
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
        # SAM1:0x801F gates the carry/snap branch on DS:6EC1 == 0.
        # Python stores that normal-jump flag as Player.jump_anim_timer.
        # Without this guard, a player who jumps from a moving platform can be
        # snapped back to actor_y-0x10 every actor tick; the carry branch also
        # resets the fall counter, leaving the player in a permanent air pose.
        if p.jump_anim_timer > 0:
            return False
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
        """Mirror any temporary barrel/body pass-through state."""
        barrel = self._ignore_barrel_collision
        if barrel is None:
            return
        if barrel not in self.entities.barrels or not barrel.body_pass_through:
            self._ignore_barrel_collision = None
            self._ignore_barrel_collision_ticks = 0
            return
        self._ignore_barrel_collision_ticks = max(
            barrel.transient_ticks,
            1 if barrel.wall_release_active else 0,
        )

    @staticmethod
    def barrel_body_is_pass_through(barrel: PushableBarrel) -> bool:
        return barrel.body_pass_through

    @staticmethod
    def barrel_top_is_pass_through(barrel: PushableBarrel) -> bool:
        return barrel.is_transient

    @staticmethod
    def barrel_is_pass_through(barrel: PushableBarrel) -> bool:
        # Backwards-compatible name for older checks.  Gameplay paths should
        # use body/top-specific helpers because wall-release barrels are body-
        # pass-through but still top-solid.
        return barrel.body_pass_through

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
        """Enter the wall-blocked barrel pass-through mode.

        Pass 122 incorrectly mapped blocked pushes onto SAM1:0x848A..0x84E9.
        That branch is now treated as a destructive/score overlap path and is
        *not* used for wall pushing.  The wall case observed in DOS keeps the raw
        0xA7 visible and top-solid while allowing body overlap until the player
        has crossed through it; at that point the barrel is restored on the free
        side of the player.  The exact ASM store for the side-restoration step is
        still open, so this helper is deliberately small and guarded by tests.
        """
        if barrel.is_transient:
            return
        barrel.code = 0xA7
        barrel.behavior_state = 0x1388
        barrel.transient_ticks = 0
        barrel.wall_release_active = True
        barrel.wall_release_push_step = 1 if push_step > 0 else -1
        barrel.direction = -barrel.wall_release_push_step
        self._ignore_barrel_collision = barrel
        self._ignore_barrel_collision_ticks = 1

    def has_active_wall_release_barrel(self) -> bool:
        return any(getattr(barrel, "wall_release_active", False) for barrel in self.entities.barrels)

    def update_wall_release_barrels(self) -> None:
        """Maintain/snap barrels in the wall-pass-through release window.

        The DOS wall case is not the destructive 0x1389 score branch: the raw
        barrel remains visible/top-solid while the player can pass through its
        body.  Pass 124 waited for a live front-wall probe, which made the
        handoff happen too late.  The useful ASM evidence is the raw-0xA7
        actor/player rectangle at SAM1:0x83C4..0x842F: both X intervals are
        `x+3..x+12`.  Restore the barrel once the player's leading shrunken
        edge has crossed the barrel's leading shrunken edge, then place the
        barrel just outside that same shrunken interval.  This makes the snap
        occur before the player's full 16px sprite touches the wall and produces
        the observed roughly ten-pixel retreat instead of a full-tile jump.
        """
        for barrel in list(self.entities.barrels):
            if not getattr(barrel, "wall_release_active", False):
                continue
            if not self.player_barrel_actor_overlap(barrel):
                barrel.wall_release_active = False
                barrel.wall_release_push_step = 0
                if self._ignore_barrel_collision is barrel:
                    self._ignore_barrel_collision = None
                    self._ignore_barrel_collision_ticks = 0
                continue
            push_step = 1 if barrel.wall_release_push_step >= 0 else -1
            if not self.player_crossed_wall_release_barrel(barrel, push_step):
                continue
            if not self.restore_wall_release_barrel_to_free_side(barrel, push_step):
                continue

    def player_crossed_wall_release_barrel(self, barrel: PushableBarrel, push_step: int) -> bool:
        """Return whether the player crossed the barrel's leading ASM edge.

        SAM1:0x83C4..0x842F uses inclusive shrunken X intervals (`x+3..x+12`)
        for both the player and the raw-0xA7 actor.  For a right-wall push, the
        handoff should occur as soon as the player's right shrunken edge reaches
        the barrel's right shrunken edge; the mirrored left case uses the left
        shrunken edge.  This is earlier than checking a full body probe against
        the wall and avoids the pass-124 late snap.
        """
        p = self.player
        if push_step > 0:
            return p.x + PLAYER_COLLISION_RIGHT >= barrel.x + PLAYER_COLLISION_RIGHT
        return p.x + PLAYER_COLLISION_LEFT <= barrel.x + PLAYER_COLLISION_LEFT

    def player_front_wall_for_barrel_release(self, push_step: int) -> bool:
        """Legacy pass-124 probe kept for old diagnostics.

        The active handoff no longer waits for this probe: DOS observation and
        the raw-0xA7 ASM overlap rectangle indicate that the barrel retreats
        before the full 16px player sprite reaches the wall.
        """
        p = self.player
        if push_step > 0:
            sample_x = int(p.x + PLAYER_COLLISION_RIGHT + 1)
        else:
            sample_x = int(p.x + PLAYER_COLLISION_LEFT - 1)
        tile_x = sample_x // TILE
        top_y = int(p.y + PLAYER_COLLISION_TOP) // TILE
        bottom_y = int(p.y + PLAYER_COLLISION_BOTTOM) // TILE
        return self.cell_blocks_body(tile_x, top_y) or self.cell_blocks_body(tile_x, bottom_y)

    def restore_wall_release_barrel_to_free_side(self, barrel: PushableBarrel, push_step: int) -> bool:
        """Place the released barrel just outside the player's ASM rectangle.

        The snap distance is not a full 16px tile.  Using the same inclusive
        `x+3..x+12` interval as SAM1:0x83C4..0x842F, the nearest non-overlap
        position is one pixel outside the player's shrunken side:

        * right-wall case: `barrel.x + 12 < player.x + 3`, so `barrel.x = player.x - 10`;
        * left-wall case:  `player.x + 12 < barrel.x + 3`, so `barrel.x = player.x + 10`.

        This produces the small ~10/11px retreat seen in DOS instead of moving
        the barrel by a whole tile.
        """
        clearance = PLAYER_COLLISION_RIGHT - PLAYER_COLLISION_LEFT + 1
        if push_step > 0:
            candidate_x = self.player.x - clearance
        else:
            candidate_x = self.player.x + clearance
        old_x = barrel.x
        barrel.x = float(candidate_x)
        if self.barrel_collides(barrel):
            barrel.x = old_x
            return False
        barrel.wall_release_active = False
        barrel.wall_release_push_step = 0
        barrel.direction = -push_step
        if self._ignore_barrel_collision is barrel:
            self._ignore_barrel_collision = None
            self._ignore_barrel_collision_ticks = 0
        return True

    def barrel_below(self) -> PushableBarrel | None:
        p = self.player
        player_bottom = p.y + PLAYER_H
        for barrel in self.entities.barrels:
            if self.barrel_top_is_pass_through(barrel):
                continue
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
            if self.barrel_top_is_pass_through(barrel):
                continue
            horizontal = self.player_barrel_horizontal_overlap(barrel)
            vertical = prev_base <= barrel.y <= new_base
            if horizontal and vertical:
                candidates.append(float(barrel.y - PLAYER_H))
        return min(candidates) if candidates else None

    def barrel_is_falling_actor(self, barrel: PushableBarrel) -> bool:
        """Return whether raw 0xA7 is in the unsupported vertical actor phase.

        The actor prelude at SAM1:0x81C8..0x8288 computes candidate X and Y
        independently from DS:34E2/DS:34E4/DS:34E6.  Once a pushed barrel has
        no floor probe below it, the original behaves as a vertical falling actor
        rather than as a still-pushable side body.  Use an explicit lock bit so
        freshly extracted barrels are not treated as falling before their first
        support refresh, while a barrel pushed off an edge becomes unpushable
        immediately within the same player tick.
        """
        if barrel.is_transient or getattr(barrel, "wall_release_active", False):
            return False
        if barrel.grounded:
            return False
        if getattr(barrel, "falling_locked", False):
            return True
        return barrel.fall_ticks > 0 and self.barrel_landing_y(barrel, barrel.y + TILE, barrel.y + TILE + 1) is None

    def player_touching_barrel(self) -> PushableBarrel | None:
        for barrel in self.entities.barrels:
            if self.barrel_body_is_pass_through(barrel):
                continue
            if self.barrel_is_falling_actor(barrel):
                # Unsupported raw-0xA7 is in its vertical actor phase.  It may
                # still block as a body via player_dynamic_body_collides(), but
                # player side contact must not apply another horizontal push.
                continue
            if self.player_overlaps_barrel(barrel):
                return barrel
        return None

    def barrel_collides(self, barrel: PushableBarrel) -> bool:
        if self.barrel_top_is_pass_through(barrel):
            return False
        left = int(barrel.x) // TILE
        right = int(barrel.x + TILE - 1) // TILE
        top = int(barrel.y) // TILE
        bottom = int(barrel.y + TILE - 1) // TILE
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                if self.cell_solid(x, y):
                    return True
        for other in self.entities.barrels:
            if other is barrel or self.barrel_top_is_pass_through(other):
                continue
            if barrel.x + TILE - 1 >= other.x and barrel.x <= other.x + TILE - 1 and barrel.y + TILE - 1 >= other.y and barrel.y <= other.y + TILE - 1:
                return True
        return False

    def try_push_barrel(self, barrel: PushableBarrel, step: int, distance: int = BARREL_ACTOR_STEP_PX) -> bool:
        old_x = barrel.x
        push_distance = max(1, int(distance))
        barrel.x += step * push_distance
        if self.barrel_collides(barrel):
            barrel.x = old_x
            return False
        barrel.direction = step
        # Successful raw-0xA7 pushes use the actor-style 4px displacement, not
        # the player's current 1/2/4px acceleration substep. That keeps a
        # very short player tap from nudging the barrel by only one pixel.
        # After the horizontal displacement, immediately re-sample support so
        # the next actor tick can enter the pushed-off-edge fall path.
        if self.barrel_landing_y(barrel, barrel.y + TILE, barrel.y + TILE + 1) is None:
            # From this point until the next landing, the actor is in the
            # reconstructed falling phase.  player_touching_barrel() will no
            # longer return it for side pushes, so holding against the barrel
            # cannot keep sliding it horizontally while it drops past the edge.
            barrel.grounded = False
            barrel.fall_ticks = 0
            barrel.falling_locked = True
        return True

    def player_on_platform(self) -> bool:
        return self.platform_below() is not None or self.barrel_below() is not None
