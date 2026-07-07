"""Simple pooled particle system for dust, smoke, sparks, and explosion effects."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin
from random import Random
from typing import List

import pygame

from settings import MAX_ACTIVE_PARTICLES, ACCENT_GOLD, ACCENT_RED, DUST, SMOKE, SPARK, BOOST, WIDTH, HEIGHT


@dataclass
class Particle:
    """One lightweight visual particle."""

    x: float
    y: float
    vx: float
    vy: float
    life: float
    size: float
    color: tuple[int, int, int]
    kind: str = "dust"
    age: float = 0.0


class ParticleManager:
    """Maintain a reusable particle pool for performance."""

    def __init__(self) -> None:
        self.particles: List[Particle] = []
        self.seed = 44_512

    def emit(self, x: float, y: float, count: int, kind: str = "dust") -> None:
        """Spawn a burst of particles around a point."""

        rng = Random(self.seed + int(x) + int(y))
        for _ in range(count):
            angle = rng.uniform(0.0, 6.28318)
            speed = rng.uniform(40.0, 240.0)
            color = self.pick_color(kind, rng)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=cos(angle) * speed,
                    vy=sin(angle) * speed - rng.uniform(20.0, 120.0),
                    life=rng.uniform(0.35, 1.2),
                    size=rng.uniform(2.0, 6.0),
                    color=color,
                    kind=kind,
                )
            )
        self.limit_pool()

    def trail(self, x: float, y: float, vx: float, vy: float, airborne: bool, slip: float = 0.0) -> None:
        """Emit dust or smoke trails based on contact state."""

        if airborne:
            self.emit(x, y, 2, kind="smoke")
        else:
            if slip > 180.0:
                self.emit(x, y, 3, kind="smoke")
                self.emit(x, y, 2, kind="spark")
            else:
                self.emit(x, y, 1, kind="dust")

    def explosion(self, x: float, y: float) -> None:
        """Emit a stronger crash burst."""

        self.emit(x, y, 32, kind="explosion")
        self.emit(x, y, 14, kind="spark")

    def boost_flame(self, x: float, y: float) -> None:
        """Emit a short boost flame effect."""

        self.emit(x, y, 5, kind="boost")

    def update(self, dt: float) -> None:
        """Advance particle motion and cull expired entries."""

        alive: List[Particle] = []
        for particle in self.particles:
            particle.age += dt
            if particle.age >= particle.life:
                continue
            particle.vy += 220.0 * dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vx *= 0.985
            particle.vy *= 0.985
            alive.append(particle)
        self.particles = alive

    def render(self, screen: pygame.Surface, camera) -> None:
        """Render all particles in screen space."""

        for particle in self.particles:
            if particle.x < camera.x - 200 or particle.x > camera.x + WIDTH + 200:
                continue
            alpha = max(0, 255 - int(255 * (particle.age / particle.life)))
            size = max(1, int(particle.size * (1.0 - particle.age / particle.life)))
            color = (*particle.color, alpha)
            surface = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, color, (size + 1, size + 1), size)
            screen.blit(surface, (camera.world_to_screen_x(particle.x) - size, camera.world_to_screen_y(particle.y) - size))

    def pick_color(self, kind: str, rng: Random) -> tuple[int, int, int]:
        """Select a color palette for a particle kind."""

        if kind == "dust":
            return DUST
        if kind == "smoke":
            return SMOKE
        if kind == "spark":
            return SPARK
        if kind == "boost":
            return BOOST
        if kind == "explosion":
            return ACCENT_RED if rng.random() > 0.5 else ACCENT_GOLD
        return DUST

    def limit_pool(self) -> None:
        """Keep the particle pool within the configured cap."""

        if len(self.particles) > MAX_ACTIVE_PARTICLES:
            self.particles = self.particles[-MAX_ACTIVE_PARTICLES:]
