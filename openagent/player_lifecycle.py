"""Player hurt/death/respawn lifecycle helpers.

The ASM distinguishes generic damage (loss of one life + invulnerability) from
hard-death hazards (direct DS:69F5/DS:69F6 death state).  Keeping this as a
mixin makes those rules easier to audit separately from map/entity update code.
"""

from __future__ import annotations

from .game_constants import DOS_TICK_HZ, PLAYER_DEATH_TIMER_INITIAL
from .player import Player
from .sound import SOUND_HURT, SOUND_PLAYER_DEATH


class PlayerLifecycleMixin:
    def hurt_player(self) -> None:
        # Generic damage helper mirrored from SAM1:0x53F4..0x5476 and
        # SAM1:0x6B28..0x6B71: if DS:6A40 > 1 it decrements one life, starts
        # DS:6A41/6A42 invulnerability for 0x1E ticks and plays sound 0x07.
        # With the last life it sets the death flag DS:69F5/69F6 instead.
        if self.player_dead_timer > 0 or self.hurt_flash > 0:
            return
        if self.lives > 1:
            self.lives -= 1
            self.hurt_flash = 0x1E / DOS_TICK_HZ
            self.play_sound(SOUND_HURT)
            self.player.jump_anim_timer = 0
            self.player.grounded = False
            self.player.vy = -40.0
        else:
            self.kill_player()

    def kill_player(self) -> None:
        # Hard-death branches set DS:69F5=1 and DS:69F6=0x23 directly.  They
        # bypass the 0x1E-tick invulnerability helper but still consume the
        # current life before the level/player is restarted.
        if self.player_dead_timer > 0:
            return
        self.lives = max(0, self.lives - 1)
        self.player_dead_timer = PLAYER_DEATH_TIMER_INITIAL
        self.player_death_frame_counter = 0
        self.hurt_flash = 0.0
        self.play_sound(SOUND_PLAYER_DEATH)
        self.player.vx = 0.0
        self.player.vy = 0.0
        self.player.jump_anim_timer = 0
        self.player.grounded = False

    def spawn_player(self) -> None:
        spawn = self.find_world_spawn() if self.is_world_map else self.find_spawn()
        self.player = Player(spawn[0], spawn[1])
        self._logic_accum = 0.0
        self._entity_accum = 0.0
        self.reset_teleport_state()

    def respawn_after_death(self) -> None:
        # SAM1 calls the restart/transition helper when DS:69F6 reaches zero.
        # The original flow rebuilds the mission instead of merely dropping the
        # player back onto the existing mutated map, so reset runtime level
        # state (actors, collected cells, opened doors, temporary inventory) and
        # then put the player at the mission start.  The game-over/menu path is
        # not rebuilt yet; if lives reaches zero, refill it to keep playtesting
        # possible.
        remaining_lives = self.lives
        score = self.score
        if remaining_lives <= 0:
            remaining_lives = 3
        self.player_dead_timer = 0
        self.player_death_frame_counter = 0
        self.hurt_flash = 0.0
        self.load_level(reset_player=True)
        self.lives = remaining_lives
        self.score = score
        self.player_dead_timer = 0
        self.player_death_frame_counter = 0
        self.hurt_flash = 0.0
        self._force_next_draw = True
