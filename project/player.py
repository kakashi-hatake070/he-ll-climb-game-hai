"""Player and vehicle ownership for the run state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pygame

from settings import HARD_CRASH_ANGULAR_VELOCITY, MAX_UPRIGHT_ANGLE
from vehicle import Vehicle


@dataclass
class Player:
    """Tracks the active vehicle, score, and run-specific progression."""

    save_data: Dict[str, int | float | bool]
    game: object | None = None
    vehicle: Vehicle = None  # type: ignore[assignment]
    coins: int = 0
    score: int = 0
    best_distance: int = 0
    best_score: int = 0
    crashed: bool = False

    def __post_init__(self) -> None:
        self.vehicle = Vehicle(self.save_data)
        self.coins = int(self.save_data.get("coins", 0))
        self.best_distance = int(self.save_data.get("best_distance", 0))
        self.best_score = int(self.save_data.get("best_score", 0))

    def reset(self, spawn_y: float) -> None:
        """Reset the current run state and re-place the vehicle."""

        self.vehicle.reset(spawn_y)
        self.score = 0
        self.crashed = False

    def update(self, dt: float, terrain, upgrades, sound_manager) -> None:
        """Update the vehicle and award score while the run is active."""

        self.vehicle.apply_upgrades(upgrades)
        is_crashing = getattr(self.game, "is_crashing", False)
        self.vehicle.update(dt, terrain, sound_manager, is_crashing)
        self.score = self.compute_score()
        self.detect_crash(terrain)

    def compute_score(self) -> int:
        """Calculate the current run score from distance, stunts, and coins."""

        stunt_bonus = self.vehicle.stunt_bonus
        return int(self.vehicle.x / 8 + stunt_bonus + self.coins * 5)

    def detect_crash(self, terrain) -> None:
        """End the run if the car is upside down or hits the ground too hard."""

        if abs(self.vehicle.angle) > MAX_UPRIGHT_ANGLE:
            self.vehicle.flip_timer += 1
        else:
            self.vehicle.flip_timer = 0

        if self.vehicle.flip_timer > 25:
            self.crashed = True

        if abs(self.vehicle.angular_velocity) > HARD_CRASH_ANGULAR_VELOCITY:
            self.crashed = True

        if self.vehicle.head_hit_ground(terrain):
            self.crashed = True

    def render(self, screen: pygame.Surface, camera) -> None:
        """Draw the vehicle."""

        self.vehicle.render(screen, camera)
