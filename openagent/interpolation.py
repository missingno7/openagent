from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Hashable

Point = tuple[float, float]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_point(previous: Point, current: Point, t: float) -> Point:
    return lerp(previous[0], current[0], t), lerp(previous[1], current[1], t)


def follow_alpha(dt: float, rate_hz: float) -> float:
    """Return a framerate-independent exponential follow coefficient.

    ``rate_hz`` is intentionally a presentation parameter, not a gameplay
    clock.  Higher values follow the target more tightly; lower values absorb
    more fixed-tick/integer jitter.  The formula keeps the perceived smoothing
    stable at different Tk callback rates.
    """
    if dt <= 0.0 or rate_hz <= 0.0:
        return 1.0
    return clamp01(1.0 - math.exp(-dt * rate_hz))


@dataclass
class PresentationSmoother:
    """Small render-only pose smoother shared by players, actors and camera.

    The fixed DOS simulation still advances on integer/fixed-tick state.  This
    object only remembers the last *displayed* floating-point position for a
    render track and lets it chase the latest interpolated target.  Large jumps
    snap immediately so teleports, level loads and object spawns do not smear.
    """

    positions: dict[Hashable, Point] = field(default_factory=dict)

    def reset(self) -> None:
        self.positions.clear()

    def forget_prefix(self, prefix: Hashable, active_keys: set[Hashable]) -> None:
        for key in list(self.positions):
            if isinstance(key, tuple) and key and key[0] == prefix and key not in active_keys:
                del self.positions[key]

    def point(
        self,
        key: Hashable,
        target: Point,
        *,
        dt: float,
        rate_hz: float,
        snap_distance: float,
    ) -> Point:
        previous = self.positions.get(key)
        if previous is None:
            self.positions[key] = target
            return target

        dx = target[0] - previous[0]
        dy = target[1] - previous[1]
        if dx * dx + dy * dy >= snap_distance * snap_distance:
            self.positions[key] = target
            return target

        alpha = follow_alpha(dt, rate_hz)
        value = (previous[0] + dx * alpha, previous[1] + dy * alpha)
        if abs(value[0] - target[0]) < 1e-3 and abs(value[1] - target[1]) < 1e-3:
            value = target
        self.positions[key] = value
        return value
