"""Small physics helpers and camera logic."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin

from settings import CAMERA_LERP_X, CAMERA_LERP_Y, clamp, lerp


@dataclass
class Camera:
    """Smooth side-scrolling camera with mild vertical lag."""

    screen_width: int
    screen_height: int
    x: float = 0.0
    y: float = 0.0
    shake_x: float = 0.0
    shake_y: float = 0.0

    def reset(self) -> None:
        """Reset the camera to the origin."""

        self.x = 0.0
        self.y = 0.0
        self.shake_x = 0.0
        self.shake_y = 0.0

    def follow(self, target_x: float, target_y: float, dt: float) -> None:
        """Ease the camera toward the target vehicle."""

        self.x += (target_x - self.x) * CAMERA_LERP_X
        self.y += (target_y - self.y) * CAMERA_LERP_Y
        self.shake_x *= 0.9
        self.shake_y *= 0.9

    def add_shake(self, intensity: float) -> None:
        """Add a short crash or landing shake impulse."""

        self.shake_x += intensity
        self.shake_y += intensity * 0.5

    def world_to_screen_x(self, x: float) -> float:
        """Convert a world X coordinate into screen space."""

        return x - self.x + self.screen_width * 0.28 + self.shake_x

    def world_to_screen_y(self, y: float) -> float:
        """Convert a world Y coordinate into screen space."""

        return y - self.y + self.screen_height * 0.55 + self.shake_y


def body_point(px: float, py: float, angle: float, lx: float, ly: float) -> tuple[float, float]:
    """Convert a local body point into world coordinates."""

    c = cos(angle)
    s = sin(angle)
    return px + lx * c - ly * s, py + lx * s + ly * c


def body_velocity_at_point(vx: float, vy: float, angular_velocity: float, cx: float, cy: float, px: float, py: float) -> tuple[float, float]:
    """Return the velocity of a point on a rotating body."""

    rx = px - cx
    ry = py - cy
    return vx - angular_velocity * ry, vy + angular_velocity * rx


def apply_force(mass: float, force_x: float, force_y: float, dt: float) -> tuple[float, float]:
    """Convert a force vector to a velocity delta."""

    return force_x / mass * dt, force_y / mass * dt


def clamp_angle(value: float) -> float:
    """Limit angle values to a practical rotation range."""

    return clamp(value, -3.14159, 3.14159)


def lerp_vector(start: float, end: float, amount: float) -> float:
    """Alias for lerp to keep physics code readable."""

    return lerp(start, end, amount)
