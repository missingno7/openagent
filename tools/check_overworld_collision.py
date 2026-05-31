#!/usr/bin/env python3
"""Regression smoke test for ASM-backed level-0 overworld collision.

Pass 99 switched level 0 to the dedicated ASM world-map parser table.  This check keeps
that from regressing by exercising the same OverworldMixin public helpers that
the runtime uses.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.animation import PLAYER_STATE_IDLE_LEFT, PLAYER_STATE_WALK_LEFT, PLAYER_STATE_WALK_RIGHT, PLAYER_WALK_COUNTER_START
from openagent.game_assets.constants import LEVEL_W, TILE
from openagent.level_model import build_runtime_collision_grid, iter_map_cells
from openagent.loader import load_campaign
from openagent.overworld import OverworldMixin
from openagent.player import Player


class OverworldProbe(OverworldMixin):
    def __init__(self, episode_number: int, level_info, *, episode=None) -> None:
        self.episode_number = episode_number
        self.episode = episode if episode is not None else SimpleNamespace(levels=[level_info], tiles16={})
        self.player = Player()
        self.collision_enabled = True
        self.keys: set[str] = set()
        self.last_world_position = None
        self.world_camera_x = 0
        self.world_camera_y = 0
        self.completed_world_levels_by_episode: dict[int, set[int]] = {}
        self.world_entry_release_level = None
        self.level_index = 0
        self._logic_accum = 0.0
        self._grid = build_runtime_collision_grid(level_info, world_map=True)

    def runtime_collision_cell(self, x: int, y: int):
        return self._grid.get((x, y))

    def snapshot_player_render_position(self) -> None:
        pass

    def update_teleport_tick(self) -> bool:
        return False

    def check_teleporter_touch(self) -> None:
        pass


def first_cell(level_info, code: int, *, body_solid: bool | None = None):
    grid = build_runtime_collision_grid(level_info, world_map=True)
    for cell in iter_map_cells(level_info):
        if cell.code != code:
            continue
        runtime = grid.get((cell.x, cell.y))
        solid = bool(runtime and runtime.body_solid)
        if body_solid is None or solid == body_solid:
            return cell
    raise AssertionError(f"No level-0 cell found for code 0x{code:02X} with body_solid={body_solid!r}")


def assert_player_rect_clear(probe: OverworldProbe, tile_x: int, tile_y: int) -> None:
    # Put the 10x16 ASM player body rect entirely inside this tile.
    x = tile_x * TILE
    y = tile_y * TILE
    assert probe.world_player_clear_at(x, y), f"expected clear at tile ({tile_x},{tile_y})"


def assert_player_rect_blocked(probe: OverworldProbe, tile_x: int, tile_y: int) -> None:
    # Put all four probes inside this tile.  This catches regressions back to
    # raw-code classification while avoiding boundary overlap with neighbors.
    x = tile_x * TILE
    y = tile_y * TILE
    assert not probe.world_player_clear_at(x, y), f"expected blocked at tile ({tile_x},{tile_y})"


def check_episode(episode) -> None:
    level0 = episode.levels[0]
    probe = OverworldProbe(episode.number, level0, episode=episode)

    water = first_cell(level0, 0x55, body_solid=True)
    assert probe.world_cell_blocked(water.x, water.y), "world parser marks raw 0x55 body-solid"
    assert_player_rect_blocked(probe, water.x, water.y)

    tree = first_cell(level0, 0x43, body_solid=True)
    assert probe.world_cell_blocked(tree.x, tree.y), "runtime body-solid tree cell should block"
    assert_player_rect_blocked(probe, tree.x, tree.y)

    cliff = first_cell(level0, 0x61, body_solid=True)
    assert probe.world_cell_blocked(cliff.x, cliff.y), "world parser marks raw 0x61 body-solid"
    assert_player_rect_blocked(probe, cliff.x, cliff.y)

    visual_corner = first_cell(level0, 0x30, body_solid=False)
    assert not probe.world_cell_blocked(visual_corner.x, visual_corner.y), "ASM world parser leaves raw 0x30 body-clear"

    # 0x20 used to be included in the broad visual blocked heuristic.  In the
    # pass-98 model it is passable unless runtime +0x1CC says otherwise.
    blank = first_cell(level0, 0x20, body_solid=False)
    assert not probe.world_cell_blocked(blank.x, blank.y), "0x20 must not be raw-code blocked"
    assert_player_rect_clear(probe, blank.x, blank.y)


    # Pass 101/102: 0x4D/0x4E is one wide building, so adding 0x4E to the
    # trigger family must not create a seventeenth entrance anchor.  Completed
    # houses remain re-enterable: the post-return release gate suppresses only
    # the tick where the player origin is still inside the same footprint.
    entrances = probe.world_entrances()
    assert len(entrances) == 16, f"episode {episode.number} should expose 16 world entrances, got {len(entrances)}"
    wide_level = next((idx + 1 for idx, (x, y, _level) in enumerate(entrances)
                       if any(c.code == 0x4D and c.x == x and c.y == y for c in iter_map_cells(level0))), None)
    assert wide_level is not None, "expected at least one 0x4D/0x4E wide entrance"
    wide_cells = probe.world_entrance_source_cells(wide_level)
    assert [c.code for c in wide_cells] == [0x4D, 0x4E], "0x4D entrance footprint includes its 0x4E right half"

    entrance_x, entrance_y, entrance_level = entrances[0]
    probe.completed_world_levels().add(entrance_level)
    probe.world_entry_release_level = entrance_level
    probe.player = Player(entrance_x * TILE, entrance_y * TILE)
    assert probe.world_entrance_level_at_player() is None, "return gate suppresses immediate completed-house re-entry"
    probe.player = Player(entrance_x * TILE - 1, entrance_y * TILE)
    assert probe.world_entrance_level_at_player() is None, "origin outside the house clears the release gate without re-entering"
    probe.player = Player(entrance_x * TILE, entrance_y * TILE)
    assert probe.world_entrance_level_at_player() == entrance_level, "completed houses stay active after leaving and walking back in"

    spawn = first_cell(level0, 0x59)
    assert probe.find_world_spawn() == (float(spawn.x * TILE), float(spawn.y * TILE)), "world spawn uses raw DS:34EE/34F0 origin, not sprite offset"

    # Pass 101: keyboard/draw state uses the normal DS:3500/34F6 player
    # animation family instead of a fixed bank-13 sprite.
    probe.player = Player(32, 32)
    probe.update_world_player_animation_state(left=False, right=True, up=False, down=False)
    assert probe.player.anim_state == PLAYER_STATE_WALK_RIGHT and probe.player.walk_counter > PLAYER_WALK_COUNTER_START
    probe.update_world_player_animation_state(left=True, right=False, up=False, down=False)
    assert probe.player.anim_state == PLAYER_STATE_WALK_LEFT
    probe.update_world_player_animation_state(left=False, right=False, up=False, down=False)
    assert probe.player.anim_state == PLAYER_STATE_IDLE_LEFT and probe.player.walk_counter == PLAYER_WALK_COUNTER_START

    # Pass 100: the world map should not clamp attempted movement to the 16px
    # sprite bounds before calling the ASM helper.  The helper itself permits
    # the player origin to reach x=LEVEL_W*16-13 because only x+12 is probed.
    # Use a synthetic empty grid so the assertion tests the geometry rather
    # than depending on episode-specific shoreline terrain.
    edge_probe = OverworldProbe(episode.number, level0, episode=episode)
    edge_probe._grid = {}
    assert edge_probe.world_player_clear_at(LEVEL_W * TILE - 13, TILE), "right-edge origin uses collision rect, not sprite width"
    assert not edge_probe.world_player_clear_at(LEVEL_W * TILE - 12, TILE), "x+12 probe still blocks outside the level"

    # Camera register update follows SAM1:0xBAF5 thresholds rather than the
    # generic center-on-player camera.
    probe.player = Player(200, 100)
    probe.world_camera_x = 0
    probe.world_camera_y = 0
    probe.collision_enabled = False
    probe.move_world_right(4)
    assert probe.world_camera_x == 4 and probe.player.x == 204, "right move scrolls once player crosses cam+0xAA"
    probe.move_world_down()
    assert probe.world_camera_y == 4 and probe.player.y == 104, "down move scrolls once player crosses cam+0x50"


def main() -> int:
    campaign = load_campaign(ROOT / "game_data")
    try:
        for episode in campaign.bundle.episodes.values():
            check_episode(episode)
    finally:
        campaign.cleanup()
    print("Overworld pass102 collision/motion/entry smoke OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
