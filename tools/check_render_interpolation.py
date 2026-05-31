#!/usr/bin/env python3
"""Regression checks for fixed-tick render interpolation.

These checks are deliberately GUI-free. They exercise the interpolation helper
methods with tiny dummy objects so we can catch timing regressions without
opening a Tk window.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import inspect
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openagent.game_constants import DOS_TICK_HZ
from openagent.interpolation import PresentationSmoother
from openagent.runtime import OpenAgentApp


@dataclass
class DummyPlayer:
    x: float = 0.0
    y: float = 0.0


@dataclass
class DummyActor:
    x: float = 0.0
    y: float = 0.0


class DummyApp:
    visual_interpolation_enabled = True
    visual_interpolation_smoothing = False
    is_world_map = False

    def __init__(self) -> None:
        self.player = DummyPlayer()
        self._prev_player_render_pos = (0.0, 0.0)
        self._logic_accum = 0.0
        self._entity_accum = 0.0
        self._last_render_dt = 1.0 / 60.0
        self.world_camera_x = 0.0
        self.world_camera_y = 0.0
        self._prev_world_camera = (0.0, 0.0)
        self._prev_entity_render_pos = {}
        self._presentation_smoother = PresentationSmoother()

    snapshot_player_render_position = OpenAgentApp.snapshot_player_render_position
    snapshot_world_camera_render_position = OpenAgentApp.snapshot_world_camera_render_position
    render_interpolation_alpha = OpenAgentApp.render_interpolation_alpha
    render_interpolation_target = OpenAgentApp.render_interpolation_target
    presentation_point = OpenAgentApp.presentation_point
    mission_camera_target = OpenAgentApp.mission_camera_target
    render_interpolation_smooth_enabled = OpenAgentApp.render_interpolation_smooth_enabled
    render_coord = staticmethod(OpenAgentApp.render_coord)
    player_render_position = OpenAgentApp.player_render_position
    entity_render_position = OpenAgentApp.entity_render_position
    camera = OpenAgentApp.camera
    viewport_size = lambda self: (320, 200)  # noqa: E731 - compact dummy method


def main() -> int:
    tick_dt = 1.0 / DOS_TICK_HZ

    tick_source = inspect.getsource(OpenAgentApp.tick)
    assert "1 / 20" not in tick_source, "fixed-timestep clamp must be larger than one DOS tick"
    assert "fixed_dt * 5.0" in tick_source, "tick() should allow several DOS ticks of catch-up"
    assert "update_mission_simulation(dt)" in tick_source, "mission ticks should be interleaved through one fixed-step loop"

    mission_source = inspect.getsource(OpenAgentApp.update_mission_simulation)
    assert mission_source.index("snapshot_dynamic_render_positions") < mission_source.index("update_entities_tick")
    assert mission_source.index("snapshot_player_render_position") < mission_source.index("update_entities_tick")
    assert mission_source.index("update_entities_tick") < mission_source.index("update_player_tick")

    alpha_source = inspect.getsource(OpenAgentApp.render_interpolation_alpha)
    assert "lookahead" not in alpha_source, "interpolation alpha should be plain linear accumulator/tick_dt"

    app = DummyApp()
    app.player.x = 0.0
    app.snapshot_player_render_position()
    app.player.x = 10.0
    # A catch-up UI frame may run a second DOS tick before drawing. The previous
    # render sample must become the state before the latest tick, not stay at 0.
    app.snapshot_player_render_position()
    app.player.x = 20.0
    assert app._prev_player_render_pos == (10.0, 0.0), app._prev_player_render_pos

    app._logic_accum = 0.0
    assert app.render_interpolation_alpha(app._logic_accum) == 0.0

    app._logic_accum = tick_dt / 2.0
    assert abs(app.render_interpolation_alpha(app._logic_accum) - 0.5) < 1e-9

    app._logic_accum = tick_dt
    assert app.render_interpolation_alpha(app._logic_accum) == 1.0

    app._prev_player_render_pos = (10.0, 0.0)
    app.player.x = 20.0
    app._logic_accum = tick_dt / 2.0
    px, py = app.player_render_position()
    assert px == 15.0, px
    assert py == 0.0

    app.visual_interpolation_smoothing = True
    app._prev_player_render_pos = (8.0, 0.0)
    app.player.x = 20.0
    app._logic_accum = tick_dt / 2.0
    smooth_mid = app.player_render_position()[0]
    assert 8.0 <= smooth_mid <= 20.0, smooth_mid
    # The first smooth sample initializes to the linear target. Subsequent
    # samples chase a moving target with a render-only filter, which makes the
    # smooth mode observably different from plain linear without touching
    # gameplay state.
    app.player.x = 24.0
    app._prev_player_render_pos = (8.0, 0.0)
    app._logic_accum = tick_dt / 2.0
    second_smooth_mid = app.player_render_position()[0]
    assert 8.0 <= second_smooth_mid <= 16.0, second_smooth_mid
    assert second_smooth_mid != 16.0, "smooth mode should not collapse to plain linear after the first sample"

    # A teleport / large snap should not smear across the screen.
    app._prev_player_render_pos = (1000.0, 0.0)
    app.player.x = 1000.0
    app._logic_accum = 0.0
    snapped = app.player_render_position()[0]
    assert snapped == 1000.0, snapped
    app.visual_interpolation_smoothing = False

    # Moving-platform regression: the platform and the carried player must use
    # the same previous fixed-tick pose and the same alpha. If the player prev
    # sample is taken after the actor tick, the player snaps to 4 while the
    # platform interpolates from 0 to 4, creating the visible platform jitter.
    platform = DummyActor(4.0, 0.0)
    app.player.x = 4.0
    app._prev_player_render_pos = (0.0, 0.0)
    app._prev_entity_render_pos = {id(platform): (0.0, 0.0)}
    app._logic_accum = tick_dt / 2.0
    player_mid = app.player_render_position()[0]
    platform_mid = app.entity_render_position(platform)[0]
    assert player_mid == platform_mid == 2.0, (player_mid, platform_mid)

    app.visual_interpolation_smoothing = True
    app._presentation_smoother.reset()
    app._prev_player_render_pos = (0.0, 0.0)
    app.player.x = 4.0
    app._prev_entity_render_pos = {id(platform): (0.0, 0.0)}
    app._logic_accum = tick_dt / 2.0
    player_smooth_mid = app.player_render_position()[0]
    platform_smooth_mid = app.entity_render_position(platform)[0]
    assert player_smooth_mid == platform_smooth_mid, (player_smooth_mid, platform_smooth_mid)
    app.visual_interpolation_smoothing = False

    app.is_world_map = True
    app._prev_world_camera = (0.0, 0.0)
    app.world_camera_x = 100.0
    app.world_camera_y = 0.0
    app._logic_accum = tick_dt / 2.0
    cam_x, cam_y = app.camera()
    assert cam_x == 50, cam_x
    assert cam_y == 0

    app.visual_interpolation_smoothing = True
    app._presentation_smoother.reset()
    app._prev_world_camera = (0.0, 0.0)
    app.world_camera_x = 100.0
    app._logic_accum = tick_dt / 2.0
    first_cam_x, _ = app.camera()
    app.world_camera_x = 120.0
    app._logic_accum = tick_dt / 2.0
    second_cam_x, _ = app.camera()
    assert first_cam_x <= second_cam_x <= 60, (first_cam_x, second_cam_x)
    app.visual_interpolation_smoothing = False

    print("render interpolation smoke OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
