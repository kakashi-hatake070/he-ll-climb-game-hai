"""Procedural terrain generation and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sin
from random import Random
from typing import Dict, List, Tuple

import pygame

from settings import CHUNK_BUFFER_AHEAD, CHUNK_BUFFER_BEHIND, CHUNK_SIZE, GROUND_DARK, GROUND_GREEN, WIDTH, HEIGHT
from settings import clamp


@dataclass
class TerrainChunk:
    """Generated terrain points for a fixed-width chunk."""

    index: int
    points: List[tuple[float, float]] = field(default_factory=list)


class Terrain:
    """Infinite layered terrain with chunk caching."""

    def __init__(self) -> None:
        self.base_y = HEIGHT * 0.72
        self.chunks: Dict[int, TerrainChunk] = {}
        self.seed = 34_771
        self.weather_types = ["sunny", "rain", "snow", "fog"]
        self.current_weather = "sunny"

    def spawn_y(self) -> float:
        """Return the starting ground reference height."""

        return self.height_at(160.0) - 58.0

    def reset_chunks(self) -> None:
        """Clear cached terrain so a new run starts cleanly."""

        self.chunks.clear()

    def height_at(self, x: float) -> float:
        """Return the terrain height at a world X coordinate."""

        if x < 0:
            return self.base_y
        low = sin(x * 0.0022) * 110.0
        mid = sin(x * 0.0061 + 1.5) * 48.0
        high = sin(x * 0.014 + 0.35) * 22.0
        ramp = sin(x * 0.00075 + 2.2) * 64.0
        cliff = sin(x * 0.021 + 0.9) * 10.0
        return self.base_y + low + mid + high + ramp + cliff

    def slope_at(self, x: float) -> float:
        """Return the local slope via finite differencing."""

        eps = 2.0
        return (self.height_at(x + eps) - self.height_at(x - eps)) / (2.0 * eps)

    def slope_factor(self, x: float) -> float:
        """Return a traction factor that weakens on steep slopes."""

        slope = abs(self.slope_at(x))
        return clamp(1.0 / (1.0 + slope * 0.02), 0.35, 1.0)

    def update(self, camera_x: float) -> None:
        """Load chunks around the player and drop old chunks."""

        start = int((camera_x - CHUNK_BUFFER_BEHIND) // CHUNK_SIZE) - 1
        end = int((camera_x + CHUNK_BUFFER_AHEAD) // CHUNK_SIZE) + 2
        for index in range(start, end + 1):
            if index not in self.chunks:
                self.chunks[index] = self.build_chunk(index)
        to_remove = [index for index in self.chunks if index < start - 2 or index > end + 2]
        for index in to_remove:
            del self.chunks[index]

    def build_chunk(self, index: int) -> TerrainChunk:
        """Build a smooth chunk using layered sine waves."""

        rng = Random(self.seed + index * 9973)
        points: List[tuple[float, float]] = []
        start_x = index * CHUNK_SIZE
        for step in range(0, CHUNK_SIZE + 1, 20):
            x = start_x + step
            y = self.height_at(x)
            y += sin(x * 0.03 + rng.random()) * 4.0
            points.append((x, y))
        return TerrainChunk(index=index, points=points)

    def render(self, screen: pygame.Surface, camera) -> None:
        """Draw the filled terrain silhouette and a darker soil layer."""

        visible_start = camera.x - WIDTH * 0.2
        visible_end = camera.x + WIDTH * 1.2
        points: List[tuple[float, float]] = []
        x = visible_start
        while x <= visible_end:
            points.append((camera.world_to_screen_x(x), camera.world_to_screen_y(self.height_at(x))))
            x += 18.0

        if len(points) < 2:
            return

        poly = [(points[0][0], HEIGHT + 120)] + points + [(points[-1][0], HEIGHT + 120)]
        pygame.draw.polygon(screen, GROUND_GREEN, poly)
        dark_poly = [(points[0][0], HEIGHT + 120)] + [(x, y + 40) for x, y in points] + [(points[-1][0], HEIGHT + 120)]
        pygame.draw.polygon(screen, GROUND_DARK, dark_poly)

    def pick_weather(self) -> str:
        """Randomly pick a new weather mode."""

        rng = Random(self.seed + len(self.chunks))
        self.current_weather = rng.choice(self.weather_types)
        return self.current_weather
