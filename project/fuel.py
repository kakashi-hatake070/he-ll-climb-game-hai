"""Fuel pickup spawning and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from math import sin
from random import Random
from typing import List

import pygame

from settings import ACCENT_GREEN, ACCENT_RED, WIDTH


@dataclass
class FuelCan:
    """One animated fuel pickup."""

    x: float
    y: float
    collected: bool = False
    phase: float = 0.0


class FuelManager:
    """Manage fuel pickups along the terrain."""

    def __init__(self) -> None:
        self.cans: List[FuelCan] = []
        self.seed = 99_111
        self.last_spawn_x = 0.0

    def reset(self) -> None:
        """Clear active fuel pickups."""

        self.cans.clear()
        self.last_spawn_x = 0.0

    def populate(self, terrain, center_x: float) -> None:
        """Ensure pickups exist ahead of the player."""

        if not self.cans:
            self.spawn_range(terrain, center_x + 600.0, center_x + 2800.0)

    def spawn_range(self, terrain, start_x: float, end_x: float) -> None:
        """Spawn fuel cans in a range."""

        rng = Random(self.seed + int(start_x * 0.17))
        x = start_x
        while x < end_x:
            x += rng.uniform(500.0, 900.0)
            self.cans.append(FuelCan(x=x, y=terrain.height_at(x) - rng.uniform(45.0, 90.0)))
        self.last_spawn_x = max(self.last_spawn_x, end_x)

    def update(self, dt: float, terrain, center_x: float) -> None:
        """Animate fuel cans and spawn more ahead."""

        for can in self.cans:
            can.phase += dt * 2.4
        if center_x + 2200.0 > self.last_spawn_x:
            self.spawn_range(terrain, self.last_spawn_x + 500.0, center_x + 2600.0)
        self.cans = [can for can in self.cans if not can.collected or can.x > center_x - 1200.0]

    def collect(self, player, sound_manager) -> None:
        """Collect fuel cans when the vehicle overlaps them."""

        vehicle = player.vehicle
        for can in self.cans:
            if can.collected:
                continue
            if any((wheel.x - can.x) ** 2 + (wheel.y - can.y) ** 2 < (wheel.radius + 14) ** 2 for wheel in vehicle.wheels):
                can.collected = True
                vehicle.fuel = min(100.0, vehicle.fuel + 22.0)
                sound_manager.play_fuel()
                if getattr(player, "game", None) is not None:
                    player.game.particles.emit(can.x, can.y, 7, kind="boost")

    def render(self, screen: pygame.Surface, camera) -> None:
        """Draw fuel cans with a floating effect."""

        for can in self.cans:
            if can.collected:
                continue
            sx = camera.world_to_screen_x(can.x)
            sy = camera.world_to_screen_y(can.y + sin(can.phase) * 5)
            if sx < -70 or sx > WIDTH + 70:
                continue
            rect = pygame.Rect(0, 0, 24, 32)
            rect.center = (int(sx), int(sy))
            pygame.draw.rect(screen, ACCENT_RED, rect, border_radius=6)
            pygame.draw.rect(screen, (255, 255, 255), rect.inflate(-12, -8), border_radius=4)
            pygame.draw.rect(screen, ACCENT_GREEN, (rect.centerx - 3, rect.top - 6, 6, 6), border_radius=3)
