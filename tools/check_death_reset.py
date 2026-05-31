#!/usr/bin/env python3
"""Regression smoke test for full mission reset after hard player death.

Death animation reaches DS:69F6=0 and then restarts the level.  The restart must
not re-apply the life/health value that was decremented before the death arc.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.player import Player
from openagent.player_lifecycle import PlayerLifecycleMixin


class LifecycleProbe(PlayerLifecycleMixin):
    def __init__(self) -> None:
        self.player = Player(10, 10)
        self.lives = 3
        self.score = 1234
        self.player_dead_timer = 0
        self.player_death_frame_counter = 0
        self.hurt_flash = 0.0
        self._force_next_draw = False
        self.loaded = False
        self.sounds: list[int] = []

    def play_sound(self, sound_id: int) -> None:
        self.sounds.append(sound_id)

    def load_level(self, *, reset_player: bool) -> None:
        assert reset_player is True
        self.loaded = True
        self.player = Player(32, 32)
        # Mirror OpenAgentApp.load_level(reset_player=True) for a mission.
        self.lives = 3
        self.score = 0
        self.player_dead_timer = 0
        self.player_death_frame_counter = 0
        self.hurt_flash = 0.0


def main() -> int:
    probe = LifecycleProbe()
    probe.kill_player()
    assert probe.lives == 2, "hard death consumes the current life during the death animation"
    assert probe.player_dead_timer > 0, "hard death starts the death animation"
    probe.respawn_after_death()
    assert probe.loaded, "death completion reloads the level"
    assert probe.lives == 3, "mission restart restores health/lives instead of preserving the decremented value"
    assert probe.score == 0, "mission restart keeps the same full-reset policy as load_level(reset_player=True)"
    assert probe.player_dead_timer == 0 and probe.hurt_flash == 0.0
    print("Death reset smoke OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
