"""Coin spawning, collection, and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sin
from random import Random
from typing import List

import pygame

from settings import ACCENT_DIAMOND, ACCENT_GOLD, ACCENT_SILVER, WIDTH


@dataclass
class Coin:
    """One collectible coin with a type and floating animation."""

    x: float
    y: float
    kind: str
    value: int
    collected: bool = False
    bob: float = 0.0


class CoinManager:
    """Maintain active coins and keep spawning them ahead of the player."""

    def __init__(self) -> None:
        self.coins: List[Coin] = []
        self.seed = 12_345
        self.last_spawn_x = 0.0

    def reset(self) -> None:
        """Clear all collected and active coins for a new run."""

        self.coins.clear()
        self.last_spawn_x = 0.0

    def populate(self, terrain, center_x: float) -> None:
        """Ensure a healthy spread of coins around the player."""

        if not self.coins:
            self.spawn_range(terrain, center_x - 200, center_x + 2600)

    def spawn_range(self, terrain, start_x: float, end_x: float) -> None:
        """Spawn a chain of coins in a world range."""

        rng = Random(self.seed + int(start_x * 0.25))
        x = start_x
        while x < end_x:
            x += rng.uniform(180.0, 420.0)
            kind_roll = rng.random()
            if kind_roll < 0.55:
                kind, value = "bronze", 1
            elif kind_roll < 0.8:
                kind, value = "silver", 5
            elif kind_roll < 0.95:
                kind, value = "gold", 20
            else:
                kind, value = "diamond", 100
            self.coins.append(Coin(x=x, y=terrain.height_at(x) - rng.uniform(70.0, 130.0), kind=kind, value=value))
        self.last_spawn_x = max(self.last_spawn_x, end_x)

    def update(self, dt: float, terrain, center_x: float) -> None:
        """Animate coins and top up future spawns."""

        for coin in self.coins:
            coin.bob += dt * 3.2
        if center_x + 2400 > self.last_spawn_x:
            self.spawn_range(terrain, self.last_spawn_x + 180.0, center_x + 2600.0)
        self.coins = [coin for coin in self.coins if not coin.collected or coin.x > center_x - 1400.0]

    def collect(self, player, sound_manager) -> None:
        """Collect coins when the car overlaps them."""

        vehicle = player.vehicle
        for coin in self.coins:
            if coin.collected:
                continue
            if any((wheel.x - coin.x) ** 2 + (wheel.y - coin.y) ** 2 < (wheel.radius + 10) ** 2 for wheel in vehicle.wheels):
                coin.collected = True
                player.coins += coin.value
                player.score += coin.value * 2
                sound_manager.play_coin()
                if getattr(player, "game", None) is not None:
                    player.game.particles.emit(coin.x, coin.y, 8, kind="spark")

    def render(self, screen: pygame.Surface, camera) -> None:
        """Draw the visible coin set."""

        for coin in self.coins:
            if coin.collected:
                continue
            sx = camera.world_to_screen_x(coin.x)
            sy = camera.world_to_screen_y(coin.y + sin(coin.bob) * 4)
            if sx < -60 or sx > WIDTH + 60:
                continue
            color = {
                "bronze": (205, 127, 50),
                "silver": ACCENT_SILVER,
                "gold": ACCENT_GOLD,
                "diamond": ACCENT_DIAMOND,
            }[coin.kind]
            pygame.draw.circle(screen, color, (int(sx), int(sy)), 10)
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), 6, 2)
