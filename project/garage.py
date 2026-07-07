"""Garage screen and upgrade buying UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pygame

from settings import HEIGHT, WIDTH, TEXT_MAIN, TEXT_MUTED, UI_PANEL, UI_PANEL_SOFT, ACCENT_GREEN, ACCENT_GOLD, MAX_UPGRADE_LEVEL


@dataclass
class GarageOption:
    """One upgrade option in the garage."""

    name: str
    key: str
    rect: pygame.Rect


class Garage:
    """Upgrade shop for the vehicle."""

    def __init__(self, game) -> None:
        self.game = game
        self.options: List[GarageOption] = []
        self.build_layout()

    def build_layout(self) -> None:
        """Create the garage UI layout."""

        x = int(WIDTH * 0.5 - 300)
        y = 170
        width = 600
        height = 54
        rows = [
            ("Engine", "engine_level"),
            ("Suspension", "suspension_level"),
            ("Tires", "tires_level"),
            ("Fuel Tank", "fuel_tank_level"),
            ("Boost", "boost_level"),
            ("Weight Reduction", "weight_reduction_level"),
        ]
        self.options = [GarageOption(name, key, pygame.Rect(x, y + index * 66, width, height)) for index, (name, key) in enumerate(rows)]

    def update(self, dt: float) -> None:
        """Garage currently uses no animated state."""

        return

    def handle_click(self, pos) -> None:
        """Handle mouse clicks on garage upgrade rows."""

        for option in self.options:
            if option.rect.collidepoint(pos):
                upgrades = self.game.upgrades
                current_level = getattr(upgrades, option.key)
                if current_level >= MAX_UPGRADE_LEVEL:
                    return
                cost = upgrades.cost_for(current_level)
                if self.game.player.coins < cost:
                    return
                self.game.player.coins -= cost
                upgrades.apply_purchase(option.key)
                self.game.save_progress()
                return

    def render(self, screen: pygame.Surface, player, upgrades) -> None:
        """Draw the garage screen and current upgrade levels."""

        panel = pygame.Rect(int(WIDTH * 0.5 - 340), 90, 680, 560)
        pygame.draw.rect(screen, UI_PANEL, panel, border_radius=28)
        title_font = pygame.font.SysFont("arial", 52, bold=True)
        screen.blit(title_font.render("Garage", True, TEXT_MAIN), (panel.centerx - 86, panel.top + 24))
        subtitle = pygame.font.SysFont("arial", 22, bold=False).render("Buy upgrades to improve your vehicle.", True, TEXT_MUTED)
        screen.blit(subtitle, subtitle.get_rect(center=(panel.centerx, panel.top + 92)))
        for option in self.options:
            self.draw_option(screen, option, player, upgrades)

    def draw_option(self, screen: pygame.Surface, option: GarageOption, player, upgrades) -> None:
        """Draw one upgrade row with a stat bar and cost label."""

        pygame.draw.rect(screen, UI_PANEL_SOFT, option.rect, border_radius=16)
        pygame.draw.rect(screen, (255, 255, 255), option.rect, width=1, border_radius=16)
        font = pygame.font.SysFont("arial", 24, bold=True)
        small = pygame.font.SysFont("arial", 18, bold=False)
        current_level = getattr(upgrades, option.key)
        screen.blit(font.render(option.name, True, TEXT_MAIN), (option.rect.x + 16, option.rect.y + 13))
        screen.blit(small.render(f"Level {current_level}/{MAX_UPGRADE_LEVEL}", True, TEXT_MUTED), (option.rect.x + 220, option.rect.y + 17))
        cost = upgrades.cost_for(current_level)
        screen.blit(font.render(f"{cost} coins", True, ACCENT_GOLD), (option.rect.right - 165, option.rect.y + 13))
        bar_width = 160
        fill = current_level / MAX_UPGRADE_LEVEL
        pygame.draw.rect(screen, (40, 51, 70), (option.rect.right - 320, option.rect.y + 19, bar_width, 16), border_radius=8)
        pygame.draw.rect(screen, ACCENT_GREEN, (option.rect.right - 320, option.rect.y + 19, int(bar_width * fill), 16), border_radius=8)
