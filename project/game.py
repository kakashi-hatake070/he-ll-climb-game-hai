"""Core game state and loop coordination for Hill Climb Clone."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Dict, Optional

import pygame

from coins import CoinManager
from fuel import FuelManager
from garage import Garage
from physics import Camera
from particles import ParticleManager
from player import Player
from settings import (
    BLACK,
    DEFAULT_SAVE,
    HEIGHT,
    SAVE_FILE,
    SKY_DAY_BOTTOM,
    SKY_DAY_TOP,
    TEXT_MAIN,
    WIDTH,
    clamp,
    format_coin_count,
    format_distance,
    lerp,
)
from sounds import SoundManager
from terrain import Terrain
from ui import UIManager
from upgrades import UpgradeManager


@dataclass
class GameResult:
    """Lightweight summary of a completed run."""

    distance: int = 0
    coins: int = 0
    score: int = 0


class Game:
    """Owns the full game state, menus, and gameplay transitions."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.clock_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.running = True
        self.state = "menu"
        self.time_of_day = 0.0
        self.weather_timer = 0.0
        self.result = GameResult()

        self.save_data = self.load_save()
        self.camera = Camera(WIDTH, HEIGHT)
        self.terrain = Terrain()
        self.player = Player(self.save_data, self)
        self.coin_manager = CoinManager()
        self.fuel_manager = FuelManager()
        self.particles = ParticleManager()
        self.garage = Garage(self)
        self.upgrades = UpgradeManager(self.save_data)
        self.sound = SoundManager(self.save_data)
        self.ui = UIManager(self)

        self.player.reset(self.terrain.spawn_y())
        self.coin_manager.populate(self.terrain, self.player.vehicle.x)
        self.fuel_manager.populate(self.terrain, self.player.vehicle.x)
        self.weather = "sunny"
        self.is_crashing = False
        self.crash_timer = 0.0

    def load_save(self) -> Dict[str, int | float | bool]:
        """Load persistent progression from disk or fall back to defaults."""

        if SAVE_FILE.exists():
            try:
                with SAVE_FILE.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError):
                data = {}
        else:
            data = {}

        save_data = dict(DEFAULT_SAVE)
        save_data.update(data)
        return save_data

    def save_progress(self) -> None:
        """Persist player progress to save.json."""

        self.save_data["coins"] = self.player.coins
        self.save_data["best_distance"] = max(int(self.save_data.get("best_distance", 0)), self.player.best_distance)
        self.save_data["best_score"] = max(int(self.save_data.get("best_score", 0)), self.player.score)
        self.save_data["engine_level"] = self.upgrades.engine_level
        self.save_data["suspension_level"] = self.upgrades.suspension_level
        self.save_data["tires_level"] = self.upgrades.tires_level
        self.save_data["fuel_tank_level"] = self.upgrades.fuel_tank_level
        self.save_data["boost_level"] = self.upgrades.boost_level
        self.save_data["weight_reduction_level"] = self.upgrades.weight_reduction_level
        self.save_data["sound_volume"] = self.sound.volume
        self.save_data["muted"] = self.sound.muted
        try:
            with SAVE_FILE.open("w", encoding="utf-8") as handle:
                json.dump(self.save_data, handle, indent=2)
        except OSError:
            pass

    def handle_events(self) -> bool:
        """Process window and input events. Returns False when quitting."""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.save_progress()
                return False
            self.ui.handle_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.restart_run()
                elif event.key == pygame.K_ESCAPE:
                    if self.state == "playing":
                        self.state = "menu"
                    elif self.state == "garage":
                        self.state = "menu"
                    elif self.state == "settings":
                        self.state = "menu"
                    else:
                        self.save_progress()
                        return False
        return self.running

    def restart_run(self) -> None:
        """Reset the active run without clearing long-term progress."""

        self.result = GameResult()
        self.terrain.reset_chunks()
        self.player.reset(self.terrain.spawn_y())
        self.coin_manager.reset()
        self.fuel_manager.reset()
        self.camera.reset()
        self.sound.play_menu_click()
        self.state = "playing"
        self.is_crashing = False
        self.crash_timer = 0.0
        self.coin_manager.populate(self.terrain, self.player.vehicle.x)
        self.fuel_manager.populate(self.terrain, self.player.vehicle.x)

    def update(self, dt: float) -> None:
        """Advance game simulation by dt seconds."""

        self.time_of_day = (self.time_of_day + dt * 0.02) % 1.0
        self.weather_timer += dt
        if self.weather_timer > 18.0:
            self.weather_timer = 0.0
            self.weather = self.terrain.pick_weather()

        if self.state == "menu":
            self.ui.update_menu(dt)
            return

        if self.state == "garage":
            self.garage.update(dt)
            return

        if self.state == "settings":
            return

        if self.state != "playing":
            return

        self.player.update(dt, self.terrain, self.upgrades, self.sound)
        self.terrain.update(self.player.vehicle.x)
        self.coin_manager.update(dt, self.terrain, self.player.vehicle.x)
        self.fuel_manager.update(dt, self.terrain, self.player.vehicle.x)
        
        if not self.is_crashing:
            self.coin_manager.collect(self.player, self.sound)
            self.fuel_manager.collect(self.player, self.sound)
            
        for wheel in self.player.vehicle.wheels:
            slip_speed = abs(wheel.spin * wheel.radius - self.player.vehicle.vx)
            self.particles.trail(wheel.x, wheel.y, wheel.vx, wheel.vy, not wheel.grounded, slip_speed)
            
        self.particles.update(dt)
        self.camera.follow(self.player.vehicle.x, self.player.vehicle.y, dt)
        self.ui.update_hud(self.player, self.upgrades)
        
        if not self.is_crashing:
            self.player.best_distance = max(self.player.best_distance, int(self.player.vehicle.x / 10))
            self.player.best_score = max(self.player.best_score, self.player.score)
            self.save_data["coins"] = self.player.coins

            if self.player.crashed or self.player.vehicle.fuel <= 0:
                self.is_crashing = True
                self.crash_timer = 1.6
                self.particles.explosion(self.player.vehicle.x, self.player.vehicle.y)
                self.sound.play_crash()
        else:
            self.crash_timer -= dt
            if self.crash_timer <= 0.0:
                self.is_crashing = False
                self.result.distance = int(self.player.vehicle.x / 10)
                self.result.coins = self.player.coins
                self.result.score = self.player.score
                self.state = "game_over"
                self.save_progress()

    def render(self) -> None:
        """Draw the current frame."""

        self.draw_background()
        self.terrain.render(self.screen, self.camera)
        self.particles.render(self.screen, self.camera)
        self.coin_manager.render(self.screen, self.camera)
        self.fuel_manager.render(self.screen, self.camera)
        self.player.render(self.screen, self.camera)
        self.ui.render(self.screen, self.camera, self.player, self.upgrades, self.result, self.state)

    def draw_background(self) -> None:
        """Render a soft day-night gradient with parallax hints."""

        top = self.sample_sky_color(True)
        bottom = self.sample_sky_color(False)
        gradient = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / max(1, HEIGHT - 1)
            color = [int(lerp(top[i], bottom[i], t)) for i in range(3)]
            pygame.draw.line(gradient, color, (0, y), (WIDTH, y))
        self.screen.blit(gradient, (0, 0))
        self.ui.render_parallax(self.screen, self.camera, self.time_of_day)

    def sample_sky_color(self, top: bool) -> tuple[int, int, int]:
        """Blend between day and night sky tones based on the time of day."""

        day = SKY_DAY_TOP if top else SKY_DAY_BOTTOM
        night = (14, 22, 48) if top else (25, 40, 72)
        mix = 0.5 + 0.5 * pygame.math.Vector2(1, 0).rotate(self.time_of_day * 360).x
        mix = clamp(mix, 0.0, 1.0)
        return tuple(int(lerp(night[i], day[i], mix)) for i in range(3))

    def open_garage(self) -> None:
        """Switch to the garage screen."""

        self.state = "garage"
        self.sound.play_menu_click()

    def open_settings(self) -> None:
        """Switch to a basic settings screen."""

        self.state = "settings"
        self.sound.play_menu_click()

    def open_menu(self) -> None:
        """Return to the main menu."""

        self.state = "menu"
        self.sound.play_menu_click()

    def start_game(self) -> None:
        """Start a fresh run."""

        self.restart_run()

    def quit(self) -> None:
        """Save progress and mark the game as stopped."""

        self.save_progress()
        self.running = False
