from __future__ import annotations

from .animation import actor_walk_counter_next, state1f_walk_counter_start
from .entities import Enemy, Explosion, Projectile, ScorePopup
from .exe_actor_mechanics import (
    BANK14_GUARD_BEHAVIOUR_BY_BASE_TILE,
    BANK14_GUARD_SHOOT_TIMER_RANGE_BY_BASE_TILE,
    BANK14_GUARD_SPEED_BY_BASE_TILE,
    CEILING_LASER_PROJECTILE_BANK,
    CEILING_LASER_PROJECTILE_TILES,
    STATE1E_PROJECTILE_BANK,
    STATE1E_PROJECTILE_LEFT_TILE,
    STATE1E_PROJECTILE_RIGHT_TILE,
    STATE1F_PROJECTILE_BANK,
    STATE1F_PROJECTILE_LEFT_TILE,
    STATE1F_PROJECTILE_RIGHT_TILE,
    STATE23_CONTACT_BOMB_SCORE,
    STATE23_SHRAPNEL_BANK,
    STATE23_SHRAPNEL_LEFT_TILE,
    STATE23_SHRAPNEL_RIGHT_TILE,
    STATE24_UP_LASER_PROJECTILE_BANK,
    STATE24_UP_LASER_PROJECTILE_TILES,
    STATE27_OPEN_HELMET_SCORE,
    STATE27_PROJECTILE_BANK,
    STATE27_PROJECTILE_LEFT_TILE,
    STATE27_PROJECTILE_RIGHT_TILE,
    STATE29_MONEY_BAG_FALLING_OBJECT_ID,
    STATE29_MONEY_BAG_SCORE,
    STATIONARY_SHOOTER_PROJECTILE,
    STATIONARY_SHOOTER_SPAWN_X_OFFSET,
    deterministic_range,
    object_id_is_shootable,
)
from .game_constants import ACTIVE_VIEW_H, ACTIVE_VIEW_W, DOS_TICK_HZ, PLAYER_H, PLAYER_W
from .semantics import (
    BANK14_GUARD_CODE_BY_BASE_TILE,
    BANK14_RIP_SHOT_SCORE,
    BANK14_RIP_TILE,
    score_popup_tile_for_value,
)
from .sound import SOUND_ENEMY_DEATH, SOUND_FALLING_BAG_DROP, SOUND_FIRE, SOUND_HURT, SOUND_NO_AMMO, SOUND_SCORE_1000

from secret_agent_editor.constants import LEVEL_H, LEVEL_W, TILE


class CombatMixin:
    """Projectile, enemy-hit, and combat helper logic.

    This mixin intentionally keeps behaviour identical to the pre-pass74
    runtime implementation; it only separates the large projectile/damage
    block from ``runtime.py`` so new ASM findings have a focused home.
    """

    def try_fire_projectile(self) -> bool:
        p = self.player
        if self.player_projectile_active():
            return False
        # The EXE fire-key branch checks DS:6EC1/69F5 and skips shot creation
        # while the jump routine is active.  It also exits before changing
        # DS:3500 when there are no shots available.
        if p.jump_anim_timer > 0:
            p.fire_cooldown = 0.10
            return False
        if self.ammo <= 0:
            p.fire_cooldown = 0.18
            self.play_sound(SOUND_NO_AMMO)
            return False
        self.ammo -= 1
        start_x = p.x + (PLAYER_W - 1 if p.facing > 0 else -2)
        start_y = p.y + 7
        self.entities.projectiles.append(Projectile(start_x, start_y, p.facing, speed=4 * DOS_TICK_HZ, hostile=False, bank=1, tile_right=38, tile_left=39, owner="player"))
        self.play_sound(SOUND_FIRE)
        return True

    def player_projectile_active(self) -> bool:
        # The EXE helper 0x5784 allocates a real actor slot for the player's
        # bullet (state 0x07/object 0x27).  Impact rewrites that same slot to
        # state 0x1388/object 0x187, so the player cannot fire again until the
        # impact actor has finished too.
        return any(shot.owner == "player" for shot in self.entities.projectiles)

    def active_camera(self) -> tuple[int, int]:
        p = self.player
        max_x = max(0, LEVEL_W * TILE - ACTIVE_VIEW_W)
        max_y = max(0, LEVEL_H * TILE - ACTIVE_VIEW_H)
        x = int(min(max(p.x + PLAYER_W / 2 - ACTIVE_VIEW_W / 2, 0), max_x))
        y = int(min(max(p.y + PLAYER_H / 2 - ACTIVE_VIEW_H / 2, 0), max_y))
        return x, y

    def rect_in_active_viewport(self, x: float, y: float, w: int = TILE, h: int = TILE, margin: int = 0) -> bool:
        cam_x, cam_y = self.active_camera()
        return not (
            x + w < cam_x - margin
            or x > cam_x + ACTIVE_VIEW_W + margin
            or y + h < cam_y - margin
            or y > cam_y + ACTIVE_VIEW_H + margin
        )

    def enemy_can_see_player(self, enemy) -> bool:
        """Approximate the EXE actor firing gates.

        Horizontal guards compare the player row and facing direction before
        calling projectile helper 0x5784.  The bank-12 ceiling crawler/state
        0x21 uses the same timer machinery but tests a vertical column below it
        and emits a downward laser/projectile.
        """
        if not enemy.can_shoot:
            return False
        p = self.player
        if enemy.kind == "ceiling_laser":
            # SAM1:0x9A48..0x9A78 checks player X inside actor_x-16..actor_x+16
            # and player_y below the crawler before spawning object 0x00C7.
            if not self.rect_in_active_viewport(enemy.x, enemy.y, TILE, TILE):
                return False
            player_center_x = p.x + PLAYER_W / 2
            actor_center_x = enemy.x + TILE / 2
            return abs(player_center_x - actor_center_x) < TILE and p.y > enemy.y
        if enemy.kind == "state24_up_laser":
            # SAM1:0xA1B3..0xA226: compare player_center_x against
            # actor_x-4..actor_x+4 and require the player to be above the emitter.
            if not self.rect_in_active_viewport(enemy.x, enemy.y, TILE, TILE):
                return False
            player_center_x = p.x + PLAYER_W / 2
            return (enemy.x - 4) <= player_center_x <= (enemy.x + 4) and p.y <= enemy.y
        if enemy.kind == "state27_shooter":
            # SAM1:0xAA64..0xAAED: once DS:34DA reaches 0x3C, compare
            # (player_y+8)>>4 against actor_y>>4, then require player X to be
            # in the current facing direction before spawning object 0x033B.
            left, top, right, bottom = self.actor_rect(enemy)
            if not self.rect_in_active_viewport(left, top, int(right - left + 1), int(bottom - top + 1)):
                return False
            player_row = int((p.y + 8) // TILE)
            enemy_row = int(enemy.y // TILE)
            if player_row != enemy_row:
                return False
            if enemy.direction > 0:
                return enemy.x < p.x
            return enemy.x > p.x
        if enemy.kind in {"state1e_shooter", "state1f_shooter"}:
            # States 0x1E/0x1F are two-high bank-12 actors.  Use their decoded
            # composite rect instead of the old one-tile row check, otherwise
            # shots only trigger from the lower sprite tile.
            left, top, right, bottom = self.actor_rect(enemy)
            if not self.rect_in_active_viewport(left, top, int(right - left + 1), int(bottom - top + 1)):
                return False
            player_center_y = p.y + PLAYER_H / 2
            if not (top <= player_center_y <= bottom):
                return False
            if enemy.direction > 0 and p.x <= right:
                return False
            if enemy.direction < 0 and p.x + PLAYER_W - 1 >= left:
                return False
            return True
        enemy_row = int(enemy.y) // TILE
        player_row = int(p.y + 8) // TILE
        if enemy_row != player_row:
            return False
        if enemy.direction > 0 and p.x <= enemy.x:
            return False
        if enemy.direction < 0 and p.x >= enemy.x:
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
        if enemy.kind == "ceiling_laser":
            # State 0x21 / raw 0x63 emits the vertical ceiling laser as soon as
            # the player is below its column.  The decoded laser object uses
            # bank 2 tiles 13..15; it travels downward from the crawler.
            start_x = enemy.x
            start_y = enemy.y + TILE
            self.entities.projectiles.append(
                Projectile(
                    start_x,
                    start_y,
                    0,
                    speed=8 * DOS_TICK_HZ,
                    hostile=True,
                    bank=CEILING_LASER_PROJECTILE_BANK,
                    tile_right=CEILING_LASER_PROJECTILE_TILES[0],
                    tile_left=CEILING_LASER_PROJECTILE_TILES[0],
                    dx_px=0,
                    dy_px=8,
                    anim_tiles=CEILING_LASER_PROJECTILE_TILES,
                    owner="enemy",
                )
            )
            self.play_sound(SOUND_FIRE)
            return
        if enemy.kind == "state24_up_laser":
            self.entities.projectiles.append(
                Projectile(
                    enemy.x,
                    enemy.y + 8,
                    0,
                    speed=8 * DOS_TICK_HZ,
                    hostile=True,
                    bank=STATE24_UP_LASER_PROJECTILE_BANK,
                    tile_right=STATE24_UP_LASER_PROJECTILE_TILES[0],
                    tile_left=STATE24_UP_LASER_PROJECTILE_TILES[0],
                    dx_px=0,
                    dy_px=-8,
                    anim_tiles=STATE24_UP_LASER_PROJECTILE_TILES,
                    owner="enemy",
                )
            )
            self.play_sound(SOUND_FIRE)
            return
        if enemy.kind == "state1e_shooter":
            self.entities.projectiles.append(
                Projectile(
                    enemy.x + (TILE if enemy.direction > 0 else -2),
                    enemy.y - 8,
                    enemy.direction,
                    speed=4 * DOS_TICK_HZ,
                    hostile=True,
                    bank=STATE1E_PROJECTILE_BANK,
                    tile_right=STATE1E_PROJECTILE_RIGHT_TILE,
                    tile_left=STATE1E_PROJECTILE_LEFT_TILE,
                    owner="enemy",
                )
            )
            self.play_sound(SOUND_FIRE)
            return
        if enemy.kind == "state1f_shooter":
            self.entities.projectiles.append(
                Projectile(
                    enemy.x + (TILE if enemy.direction > 0 else -2),
                    enemy.y - 8,
                    enemy.direction,
                    speed=4 * DOS_TICK_HZ,
                    hostile=True,
                    bank=STATE1F_PROJECTILE_BANK,
                    tile_right=STATE1F_PROJECTILE_RIGHT_TILE,
                    tile_left=STATE1F_PROJECTILE_LEFT_TILE,
                    owner="enemy",
                )
            )
            self.play_sound(SOUND_FIRE)
            return
        if enemy.kind == "state27_shooter":
            # SAM1:0xAAC3..0xAAED passes actor X/Y directly to helper 0x5784
            # with direction DS:34E2, speed=4 and object=0x033B.
            self.entities.projectiles.append(
                Projectile(
                    enemy.x,
                    enemy.y,
                    enemy.direction,
                    speed=4 * DOS_TICK_HZ,
                    hostile=True,
                    bank=STATE27_PROJECTILE_BANK,
                    tile_right=STATE27_PROJECTILE_RIGHT_TILE,
                    tile_left=STATE27_PROJECTILE_LEFT_TILE,
                    owner="enemy",
                )
            )
            self.play_sound(SOUND_FIRE)
            return
        if enemy.kind == "stationary_shooter":
            # EXE states 0x0A/0x0B use projectile object 0x01D6, while
            # 0x0C/0x0D use 0x01E8/0x01EC.  Those resolve to the decoded
            # bank-4 sprites below.  The helper call passes speed=4.
            bank, tile_right, tile_left = STATIONARY_SHOOTER_PROJECTILE.get(enemy.code, (1, 38, 39))
            start_x = enemy.x + STATIONARY_SHOOTER_SPAWN_X_OFFSET.get(enemy.code, TILE - 2 if enemy.direction > 0 else -2)
            start_y = enemy.y + 8
            self.entities.projectiles.append(
                Projectile(start_x, start_y, enemy.direction, speed=4 * DOS_TICK_HZ, hostile=True, bank=bank, tile_right=tile_right, tile_left=tile_left, owner="enemy")
            )
            return
        # Bank-14 shooter guards and the player share projectile helper 0x5784
        # with object_id=0.  That helper resolves to active object 0x0027,
        # displayed here as bank 1 tiles 38/39, speed=4 px/tick.
        start_x = enemy.x + (TILE - 2 if enemy.direction > 0 else -2)
        start_y = enemy.y + 8
        self.entities.projectiles.append(Projectile(start_x, start_y, enemy.direction, speed=4 * DOS_TICK_HZ, hostile=True, bank=1, tile_right=38, tile_left=39, owner="enemy"))
        self.play_sound(SOUND_FIRE)

    def spawn_lightning_bolt(self, enemy) -> None:
        # Raw 0x6E / state 0x26 calls projectile helper 0x5784 with object
        # 0x0089 at (actor_x, actor_y + 16).  Helper maps object 0x89 to state
        # 0x28 and initializes DS:34DA=0x1E; the state animates in place until
        # the timer expires.
        self.entities.projectiles.append(
            Projectile(
                enemy.x,
                enemy.y + TILE,
                0,
                hostile=True,
                bank=2,
                tile_right=36,
                tile_left=36,
                dx_px=0,
                dy_px=0,
                anim_tiles=(36, 37, 38, 39),
                owner="enemy",
                life_ticks=0x1E,
            )
        )
        self.play_sound(SOUND_FIRE)

    def spawn_projectile_explosion(self, x: float, y: float) -> None:
        # Impact branch near SAM1:0x4F15 and enemy hit branch near 0x5C59 turns
        # the projectile actor into the short hit spark.  The visible decoded
        # sprite family is bank 5 tiles 24..27, not the unrelated bank-6 frames.
        self.entities.explosions.append(Explosion(float(x - 8), float(y - 8)))

    def begin_projectile_impact(self, shot: Projectile, *, visible: bool = True, ticks: int = 12) -> None:
        # Wall/solid impacts enter the visible 0x1388/object-0x0187 impact
        # state.  Enemy hit branches also consume/rewrite the projectile slot,
        # but the visible wall-spark should not be drawn over every damaged
        # actor.  Keep the slot briefly occupied so the one-shot rule still
        # behaves like the EXE helper path.
        shot.impact_ticks = max(1, ticks)
        shot.impact_visible = visible
        shot.dx_px = 0
        shot.dy_px = 0
        shot.frame_counter = 0

    def actor_rect(self, enemy: Enemy) -> tuple[float, float, float, float]:
        # Match the decoded composite sprite origins.  The previous runtime
        # treated 0x24/0x56/0x58 as two-wide one-high actors, but the renderer
        # and EXE draw them as a vertical pair at (x,y-16)+(x,y).  0xAE is the
        # opposite: a horizontal pair at (x-16,y)+(x,y).
        if enemy.code == 0xAE:
            return enemy.x - TILE, enemy.y, enemy.x + TILE - 1, enemy.y + TILE - 1
        if enemy.code in {0x24, 0x56, 0x58}:
            return enemy.x, enemy.y - TILE, enemy.x + TILE - 1, enemy.y + TILE - 1
        return enemy.x, enemy.y, enemy.x + TILE - 1, enemy.y + TILE - 1

    def actor_contains_point(self, enemy: Enemy, x: float, y: float) -> bool:
        left, top, right, bottom = self.actor_rect(enemy)
        return left <= x <= right and top <= y <= bottom

    def enemy_is_shootable(self, enemy: Enemy) -> bool:
        if enemy.is_rip or enemy.bank == 14:
            return True
        if enemy.hp <= 0:
            return False
        return object_id_is_shootable(enemy.object_id)

    def actor_is_indestructible_solid(self, enemy: Enemy) -> bool:
        # Stationary rocket/shooter traps are actor slots for firing/timing, but
        # not entries in the EXE damage branch.  Treat them as solid map objects:
        # bullets impact and explode, but the actor is not removed or damaged.
        # Other unimplemented actor states may be harmful or non-shootable, but
        # they should not automatically become wall blocks.
        return enemy.kind == "stationary_shooter"

    def update_projectiles_tick(self) -> None:
        kept: list[Projectile] = []
        for shot in self.entities.projectiles:
            shot.frame_counter += 1
            if shot.is_impact:
                shot.impact_ticks -= 1
                if shot.impact_ticks > 0:
                    kept.append(shot)
                continue
            if shot.life_ticks > 0:
                shot.life_ticks -= 1
                if shot.hostile and self.hurt_flash <= 0 and self.projectile_hits_player_rect(shot.x, shot.y, TILE, TILE):
                    self.hurt_player()
                if shot.life_ticks > 0:
                    kept.append(shot)
                continue
            old_x, old_y = shot.x, shot.y
            shot.x += shot.dx_px if shot.dx_px is not None else shot.direction * 4
            shot.y += shot.dy_px
            if not self.projectile_in_active_viewport(shot):
                continue
            tile_x = int(shot.x) // TILE
            tile_y = int(shot.y) // TILE
            if tile_x < 0 or tile_y < 0 or tile_x >= LEVEL_W or tile_y >= LEVEL_H:
                continue
            if self.cell_blocks_body(tile_x, tile_y):
                self.begin_projectile_impact(shot)
                kept.append(shot)
                continue
            if shot.hostile:
                if self.projectile_hits_player(shot, old_x, old_y):
                    self.hurt_player()
                    # Hostile projectiles are consumed by the player hit.  Do
                    # not draw the wall-impact spark on the player body.
                    continue
                kept.append(shot)
                continue
            blocked_by_actor = None
            hit = None
            for enemy in self.entities.enemies:
                if self.projectile_crosses_actor(shot, enemy, old_x, old_y):
                    if self.enemy_is_shootable(enemy):
                        hit = enemy
                        break
                    if self.actor_is_indestructible_solid(enemy):
                        blocked_by_actor = enemy
                        break
            if hit is not None:
                self.hit_enemy_with_projectile(hit, shot)
                # The big 0x0187 wall-spark is only for solid impacts.  On
                # normal enemy hits the actor itself flashes/changes state, so
                # consume the player shot without drawing an extra explosion.
                self.begin_projectile_impact(shot, visible=False, ticks=4)
                kept.append(shot)
                continue
            if blocked_by_actor is not None:
                self.begin_projectile_impact(shot)
                kept.append(shot)
                continue
            kept.append(shot)
        self.entities.projectiles = kept

    def projectile_hits_player(self, shot: Projectile, old_x: float | None = None, old_y: float | None = None) -> bool:
        p = self.player
        return self.segment_hits_rect(
            old_x if old_x is not None else shot.x,
            old_y if old_y is not None else shot.y,
            shot.x,
            shot.y,
            p.x,
            p.y,
            p.x + PLAYER_W - 1,
            p.y + PLAYER_H - 1,
        )

    def projectile_hits_player_rect(self, x: float, y: float, w: int, h: int) -> bool:
        p = self.player
        return not (
            p.x + PLAYER_W - 1 < x
            or p.x > x + w - 1
            or p.y + PLAYER_H - 1 < y
            or p.y > y + h - 1
        )

    def projectile_crosses_actor(self, shot: Projectile, enemy: Enemy, old_x: float, old_y: float) -> bool:
        left, top, right, bottom = self.actor_rect(enemy)
        return self.segment_hits_rect(old_x, old_y, shot.x, shot.y, left, top, right, bottom)

    def projectile_in_active_viewport(self, shot: Projectile) -> bool:
        # Projectile actors are culled by the fixed DOS gameplay viewport, not
        # the whole level and not the resized editor window.  Use a small sprite
        # footprint so a bullet disappears only once it has fully left view.
        return self.rect_in_active_viewport(shot.x - 8, shot.y - 8, 16, 16)

    def segment_hits_rect(self, x1: float, y1: float, x2: float, y2: float, left: float, top: float, right: float, bottom: float) -> bool:
        steps = max(1, int(max(abs(x2 - x1), abs(y2 - y1))))
        for i in range(steps + 1):
            t = i / steps
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t
            if left <= x <= right and top <= y <= bottom:
                return True
        return False

    def enemy_overlaps_player(self, enemy: Enemy) -> bool:
        p = self.player
        left, top, right, bottom = self.actor_rect(enemy)
        return not (
            p.x + PLAYER_W - 1 < left
            or p.x > right
            or p.y + PLAYER_H - 1 < top
            or p.y > bottom
        )

    def money_bag_tight_overlap(self, enemy: Enemy) -> bool:
        # SAM1:0xB12B..0xB144 and 0xB4C6..0xB4E5 use signed deltas with
        # thresholds around +/-8 for the idle trigger and +/-10 for collection.
        p = self.player
        return abs((p.x + PLAYER_W / 2) - (enemy.x + TILE / 2)) < 10 and abs((p.y + PLAYER_H / 2) - (enemy.y + TILE / 2)) < 10

    def arm_money_bag_drop(self, enemy: Enemy) -> None:
        # The EXE scans upward in tile-sized steps until it hits body collision,
        # then rewrites the slot to object 0x026B with speed metadata 8.  Use
        # the nearest solid tile above as the ceiling origin, falling from just
        # below it.  If no ceiling is found, keep the current Y so maps without
        # the matching setup still behave sensibly.
        tile_x = max(0, min(LEVEL_W - 1, int(enemy.x + TILE / 2) // TILE))
        current_tile_y = max(0, min(LEVEL_H - 1, int(enemy.y) // TILE))
        for ty in range(current_tile_y - 1, -1, -1):
            if self.cell_blocks_body(tile_x, ty):
                enemy.y = float((ty + 1) * TILE)
                break
        enemy.object_id = STATE29_MONEY_BAG_FALLING_OBJECT_ID
        enemy.step_px = 8
        enemy.frame_counter = 1
        # SAM1:0xB173 uses sound 0x09 when raw 0x5B arms into falling object 0x026B.
        self.play_sound(SOUND_FALLING_BAG_DROP)

    def collect_money_bag_actor(self, enemy: Enemy) -> None:
        if enemy not in self.entities.enemies:
            return
        self.entities.enemies.remove(enemy)
        self.score += STATE29_MONEY_BAG_SCORE
        self.spawn_score_popup(enemy.x, enemy.y, STATE29_MONEY_BAG_SCORE)
        self.spawn_projectile_explosion(enemy.x + TILE / 2, enemy.y + TILE / 2)
        self.play_sound(SOUND_SCORE_1000)

    def explode_contact_bomb(self, enemy: Enemy) -> None:
        if enemy not in self.entities.enemies:
            return
        self.entities.enemies.remove(enemy)
        self.score += STATE23_CONTACT_BOMB_SCORE
        self.spawn_score_popup(enemy.x, enemy.y, STATE23_CONTACT_BOMB_SCORE)
        self.spawn_projectile_explosion(enemy.x + TILE / 2, enemy.y + TILE / 2)
        self.entities.projectiles.append(
            Projectile(
                enemy.x - 2,
                enemy.y + 8,
                -1,
                speed=4 * DOS_TICK_HZ,
                hostile=True,
                bank=STATE23_SHRAPNEL_BANK,
                tile_right=STATE23_SHRAPNEL_RIGHT_TILE,
                tile_left=STATE23_SHRAPNEL_LEFT_TILE,
                owner="enemy",
            )
        )
        self.entities.projectiles.append(
            Projectile(
                enemy.x + TILE - 2,
                enemy.y + 8,
                1,
                speed=4 * DOS_TICK_HZ,
                hostile=True,
                bank=STATE23_SHRAPNEL_BANK,
                tile_right=STATE23_SHRAPNEL_RIGHT_TILE,
                tile_left=STATE23_SHRAPNEL_LEFT_TILE,
                owner="enemy",
            )
        )
        self.play_sound(SOUND_ENEMY_DEATH)

    def spawn_score_popup(self, x: float, y: float, value: int, *, preferred_tile: int | None = None) -> None:
        popup_tile = preferred_tile if preferred_tile is not None else score_popup_tile_for_value(value)
        if popup_tile is None:
            # The original popup sprite set only has fixed denominations up to
            # 10K; use the largest visible score marker for larger bonuses.
            popup_tile = score_popup_tile_for_value(10000)
        if popup_tile is not None:
            self.entities.score_popups.append(ScorePopup(float(x), float(y - 8), value, popup_tile))

    def hit_enemy_with_projectile(self, enemy, shot: Projectile | None = None) -> None:
        if enemy.kind == "state27_shooter":
            # Raw 0x24 / object 0x0065 has an object-specific hit branch and
            # the state-0x27 update only enters the death/score path while
            # DS:34DE == 0.  During the walking/closed-helmet phase the EXE
            # plays sound 0x08 but does not damage/remove the actor.
            if enemy.phase_ticks > 0:
                # Closed helmet ping: the object-specific hit branch still
                # gives the actor the same short white feedback, but does not
                # decrement HP or kill it.
                enemy.hit_flash_ticks = 3
                enemy.alert_ticks = 8
                self.play_sound(SOUND_HURT)
                return
            if enemy in self.entities.enemies:
                self.entities.enemies.remove(enemy)
            self.score += STATE27_OPEN_HELMET_SCORE
            self.spawn_score_popup(enemy.x, enemy.y, STATE27_OPEN_HELMET_SCORE)
            self.spawn_projectile_explosion(enemy.x + TILE / 2, enemy.y - TILE / 2)
            self.spawn_projectile_explosion(enemy.x + TILE / 2, enemy.y + TILE / 2)
            self.play_sound(SOUND_ENEMY_DEATH)
            return
        if enemy.is_rip:
            self.entities.enemies.remove(enemy)
            self.score += BANK14_RIP_SHOT_SCORE
            self.spawn_score_popup(enemy.x, enemy.y, BANK14_RIP_SHOT_SCORE)
            self.play_sound(SOUND_ENEMY_DEATH)
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
                enemy.hit_flash_ticks = 3
                self.play_sound(SOUND_HURT)
                return

            enemy.kind = "rip"
            enemy.base_tile = BANK14_RIP_TILE
            enemy.step_px = 0
            enemy.shoot_interval_ticks = 0
            enemy.shoot_timer_ticks = 0
            enemy.frame_counter = 0
            self.play_sound(SOUND_ENEMY_DEATH)
            return
        if enemy.hp > 1:
            enemy.hp -= 1
            enemy.hit_flash_ticks = 3
            enemy.alert_ticks = 8
            if shot is not None and enemy.code != 0xAE:
                enemy.direction = -1 if shot.x > enemy.x else 1
                if enemy.code == 0x58:
                    enemy.frame_counter = state1f_walk_counter_start(enemy.direction)
            self.play_sound(SOUND_HURT)
            return
        self.entities.enemies.remove(enemy)
        self.score += 100
        self.spawn_score_popup(enemy.x, enemy.y, 100)
        self.play_sound(SOUND_ENEMY_DEATH)

