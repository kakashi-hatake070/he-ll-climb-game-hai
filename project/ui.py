"""Menu and HUD rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sin, cos
from typing import List, Tuple

import pygame

from settings import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_RED,
    BLACK,
    HEIGHT,
    TEXT_MAIN,
    TEXT_MUTED,
    UI_BORDER,
    UI_PANEL,
    UI_PANEL_SOFT,
    WIDTH,
    clamp,
    format_coin_count,
    format_distance,
)


@dataclass
class MenuButton:
    """Clickable menu button with hover animation state."""

    label: str
    rect: pygame.Rect
    action: str
    hover: float = 0.0


class UIManager:
    """Draw HUD, menu, garage, and game over overlays."""

    def __init__(self, game) -> None:
        self.game = game
        self.buttons: List[MenuButton] = []
        self.build_menu_buttons()
        self._warn_flash = 0.0   # oscillates 0→1→0 for animated blink
        self._warn_dt_acc = 0.0  # accumulate dt for flashing

    def build_menu_buttons(self) -> None:
        """Create the main menu button layout."""

        x = WIDTH * 0.5 - 160
        y = HEIGHT * 0.42
        labels = [("Start Game", "start"), ("Garage", "garage"), ("Upgrade", "garage"), ("Settings", "settings"), ("Exit", "exit")]
        self.buttons = []
        for index, (label, action) in enumerate(labels):
            self.buttons.append(MenuButton(label, pygame.Rect(int(x), int(y + index * 72), 320, 56), action))

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route mouse clicks to buttons and screen actions."""

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self.game.state == "menu":
            for button in self.buttons:
                if button.rect.collidepoint(event.pos):
                    self.game.sound.play_menu_click()
                    if button.action == "start":
                        self.game.start_game()
                    elif button.action == "garage":
                        self.game.open_garage()
                    elif button.action == "settings":
                        self.game.open_settings()
                    elif button.action == "exit":
                        self.game.quit()
        elif self.game.state == "garage":
            self.game.garage.handle_click(event.pos)
        elif self.game.state == "settings":
            self.handle_settings_click(event.pos)

    def update_menu(self, dt: float) -> None:
        """Animate menu hover states."""

        mouse = pygame.mouse.get_pos()
        for button in self.buttons:
            button.hover = clamp(button.hover + (1 if button.rect.collidepoint(mouse) else -1) * dt * 4.0, 0.0, 1.0)

    def update_hud(self, player, upgrades) -> None:
        """Update cached HUD values if needed."""

        self.player_ref = player
        self.upgrades_ref = upgrades

    def render(self, screen: pygame.Surface, camera, player, upgrades, result, state: str) -> None:
        """Render the current UI layer based on game state."""

        if state == "menu":
            self.render_menu(screen)
        elif state == "garage":
            self.game.garage.render(screen, player, upgrades)
        elif state == "settings":
            self.render_settings(screen)
        elif state == "game_over":
            self.render_game_over(screen, result)
        else:
            self.render_hud(screen, player)

    def render_parallax(self, screen: pygame.Surface, camera, time_of_day: float) -> None:
        """Render soft parallax clouds and sky atmosphere."""

        for index in range(7):
            x = (index * 220 - camera.x * 0.08) % (WIDTH + 240) - 120
            y = 88 + index * 26 + sin(time_of_day * 6.28 + index) * 12
            pygame.draw.ellipse(screen, (255, 255, 255, 42), (x, y, 180, 52))

    def render_menu(self, screen: pygame.Surface) -> None:
        """Render the main menu overlay."""

        panel = pygame.Rect(int(WIDTH * 0.5 - 210), int(HEIGHT * 0.12), 420, 560)
        pygame.draw.rect(screen, UI_PANEL, panel, border_radius=28)
        self.draw_title(screen, "Hill Climb Clone", panel.centerx, panel.top + 60)
        subtitle = self.make_font(24).render("Drive, climb, collect, upgrade.", True, TEXT_MUTED)
        screen.blit(subtitle, subtitle.get_rect(center=(panel.centerx, panel.top + 122)))
        for button in self.buttons:
            self.draw_button(screen, button)

    def render_hud(self, screen: pygame.Surface, player) -> None:
        """Render the gameplay heads-up display."""

        # 1. Top Left stats
        # Fuel
        self.draw_fuel_icon(screen, 20, 20)
        self.draw_bar(screen, 50, 22, 180, 16, player.vehicle.fuel / 100.0, (74, 222, 128))
        
        # Coins
        self.draw_coin_icon(screen, 30, 60)
        coin_font = self.make_font(26)
        coin_text = f"{player.coins:,}".replace(",", " ")
        screen.blit(coin_font.render(coin_text, True, (255, 255, 255)), (52, 48))
        
        # Diamonds
        self.draw_diamond_icon(screen, 30, 96)
        diamond_count = player.coins // 12
        screen.blit(coin_font.render(str(diamond_count), True, (255, 255, 255)), (52, 84))

        # 2. Top Right Pause Button
        self.draw_pause_button(screen, WIDTH - 45, 20)

        # 3. Bottom Pedals
        keys = pygame.key.get_pressed()
        gas_active = keys[pygame.K_RIGHT] or keys[pygame.K_d] or keys[pygame.K_w]
        brake_active = keys[pygame.K_LEFT] or keys[pygame.K_a] or keys[pygame.K_s]
        
        # Brake Pedal (Bottom Left)
        self.draw_pedal(screen, 24, HEIGHT - 164, 110, 140, "BRAKE", brake_active)
        
        # Gas Pedal (Bottom Right)
        self.draw_pedal(screen, WIDTH - 134, HEIGHT - 164, 110, 140, "GAS", gas_active)

        # 4. Bottom Gauges
        # Calculate mock RPM based on wheel contact, velocity, and tilt input
        rpm_val = 1000.0
        if player.vehicle.on_ground():
            rpm_val += abs(player.vehicle.vx) * 7.5
            if gas_active:
                rpm_val += 2200.0
        else:
            if gas_active:
                rpm_val += 5800.0
        rpm_val = clamp(rpm_val, 800.0, 8000.0)
        
        # RPM Gauge (Bottom Left-Center)
        self.draw_gauge(screen, WIDTH * 0.5 - 75, HEIGHT - 85, 55, rpm_val, 8000.0, "RPM")
        
        # Speed/Boost Gauge (Bottom Right-Center)
        speed_val = abs(player.vehicle.vx) * 0.18
        self.draw_gauge(screen, WIDTH * 0.5 + 75, HEIGHT - 85, 55, speed_val, 240.0, "BOOST")
        
        # NOS Bottle
        self.draw_nos_bottle(screen, WIDTH * 0.5 - 175, HEIGHT - 105)

        # 5. Distance Display
        dist_font = self.make_font(22)
        dist_text = f"DISTANCE: {int(player.vehicle.x / 10)}m"
        text_surf = dist_font.render(dist_text, True, (255, 255, 255))
        # Draw a small background panel for distance text
        panel_rect = text_surf.get_rect(center=(WIDTH * 0.5, HEIGHT - 165))
        bg_rect = panel_rect.inflate(24, 12)
        pygame.draw.rect(screen, (15, 23, 42, 200), bg_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255, 60), bg_rect, width=1, border_radius=10)
        screen.blit(text_surf, panel_rect)

        # 6. Danger Warnings (must be last so they render on top)
        self.draw_warnings(screen, player)

    def draw_warnings(self, screen: pygame.Surface, player) -> None:
        """Draw animated warning indicators when the player is in danger."""
        import math
        
        v = player.vehicle
        now = pygame.time.get_ticks() / 1000.0  # seconds
        
        # Collect all active warnings
        warnings = []
        
        # --- WARNING 1: Low Fuel ---
        if v.fuel < 25.0:
            severity = 1.0 - (v.fuel / 25.0)   # 0.0 at 25%, 1.0 at 0%
            warnings.append(("danger" if v.fuel < 10.0 else "caution", severity, "⛽  LOW FUEL!"))
        
        # --- WARNING 2: Flip Danger (car tilting too much) ---
        tilt_deg = abs(math.degrees(v.angle))
        if tilt_deg > 38.0:
            severity = min(1.0, (tilt_deg - 38.0) / 32.0)  # 0 at 38°, 1 at 70°
            warnings.append(("danger" if tilt_deg > 58.0 else "caution", severity, "⚠  ABOUT TO FLIP!"))
        
        # --- WARNING 3: Very high speed on a hill ---
        speed = abs(v.vx)
        if speed > 700.0 and v.on_ground():
            severity = min(1.0, (speed - 700.0) / 300.0)
            warnings.append(("caution", severity, "💨  SLOW DOWN!"))
        
        # --- WARNING 4: Almost out of bounds / stuck reversed ---
        if v.vx < -30.0 and v.x < 200.0:
            warnings.append(("danger", 1.0, "↩  REVERSING TO START!"))
        
        if not warnings:
            return
        
        # Pick the highest-severity warning
        warnings.sort(key=lambda w: (w[0] == "danger", w[1]), reverse=True)
        level, severity, msg = warnings[0]
        
        # Blink speed: danger blinks fast, caution slower
        blink_speed = 6.0 if level == "danger" else 3.5
        alpha_factor = (math.sin(now * blink_speed * math.pi) * 0.5 + 0.5)  # 0..1
        
        # Screen edge danger flash (red vignette-style overlay)
        edge_thickness = int(14 + severity * 22)
        edge_alpha = int(alpha_factor * severity * 200)
        edge_color_map = {
            "danger": (220, 38, 38),
            "caution": (234, 179, 8),
        }
        edge_color = edge_color_map[level]
        
        # Draw 4 edge rectangles
        for rect in [
            pygame.Rect(0, 0, WIDTH, edge_thickness),           # top
            pygame.Rect(0, HEIGHT - edge_thickness, WIDTH, edge_thickness),  # bottom
            pygame.Rect(0, 0, edge_thickness, HEIGHT),           # left
            pygame.Rect(WIDTH - edge_thickness, 0, edge_thickness, HEIGHT),  # right
        ]:
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill((*edge_color, edge_alpha))
            screen.blit(overlay, rect.topleft)
        
        # Warning Banner — centered, top of screen
        warn_font = self.make_font(28)
        text_surf = warn_font.render(msg, True, (255, 255, 255))
        banner_w = text_surf.get_width() + 48
        banner_h = 46
        banner_x = WIDTH // 2 - banner_w // 2
        banner_y = 16
        
        banner_alpha = int(120 + alpha_factor * 135)
        banner_color = (180, 20, 20) if level == "danger" else (160, 120, 0)
        banner_surf = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        banner_surf.fill((*banner_color, banner_alpha))
        pygame.draw.rect(banner_surf, (*edge_color, 220), (0, 0, banner_w, banner_h), width=2, border_radius=12)
        screen.blit(banner_surf, (banner_x, banner_y))
        screen.blit(text_surf, text_surf.get_rect(center=(WIDTH // 2, banner_y + banner_h // 2)))
        
        # Tilt meter bar (only for flip warning)
        if tilt_deg > 38.0:
            bar_w = 200
            bar_h = 12
            bar_x = WIDTH // 2 - bar_w // 2
            bar_y = banner_y + banner_h + 8
            # Background
            pygame.draw.rect(screen, (30, 35, 45), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
            # Fill — green to red gradient based on angle
            fill_w = int(bar_w * min(1.0, tilt_deg / 90.0))
            tilt_color = (
                min(255, int(tilt_deg * 3.5)),
                max(0, 255 - int(tilt_deg * 3.0)),
                0
            )
            if fill_w > 0:
                pygame.draw.rect(screen, tilt_color, (bar_x, bar_y, fill_w, bar_h), border_radius=6)
            # Border
            pygame.draw.rect(screen, (255, 255, 255, 80), (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=6)
            # Label
            lbl_font = self.make_font(14)
            lbl = lbl_font.render(f"TILT {int(tilt_deg)}°", True, (255, 255, 255))
            screen.blit(lbl, lbl.get_rect(center=(WIDTH // 2, bar_y + bar_h + 10)))

    def draw_fuel_icon(self, screen, x, y):
        rect = pygame.Rect(x, y, 20, 26)
        pygame.draw.rect(screen, (220, 38, 38), rect, border_radius=4)
        pygame.draw.rect(screen, (255, 255, 255), (x + 3, y + 2, 4, 6), border_radius=1)
        pygame.draw.rect(screen, (15, 23, 42), (x + 6, y - 4, 8, 4), border_radius=1)

    def draw_coin_icon(self, screen, x, y):
        pygame.draw.circle(screen, (245, 158, 11), (x, y), 11)
        pygame.draw.circle(screen, (251, 191, 36), (x, y), 9)
        pygame.draw.circle(screen, (217, 119, 6), (x, y), 11, 2)

    def draw_diamond_icon(self, screen, x, y):
        points = [
            (x, y - 11),
            (x + 10, y),
            (x, y + 11),
            (x - 10, y)
        ]
        pygame.draw.polygon(screen, (6, 182, 212), points)
        pygame.draw.polygon(screen, (255, 255, 255), points, 1)

    def draw_pedal(self, screen, x, y, width, height, label, pressed):
        # Draw metal plate
        color = (130, 135, 140) if pressed else (170, 175, 180)
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, color, rect, border_radius=16)
        pygame.draw.rect(screen, (80, 85, 90), rect, width=3, border_radius=16)
        
        # Draw 6 holes
        dx = width // 3
        dy = height // 4
        for r in range(3):
            for c in range(2):
                hx = x + dx * (c + 1)
                hy = y + dy * (r + 1) - 5
                pygame.draw.circle(screen, (40, 45, 50), (hx, hy), 10)
                pygame.draw.circle(screen, (200, 205, 210), (hx, hy), 10, 1)
                
        # Draw label text
        font = self.make_font(18)
        text = font.render(label, True, (15, 23, 42))
        screen.blit(text, text.get_rect(center=(x + width // 2, y + height - 20)))

    def draw_gauge(self, screen, cx, cy, radius, value, max_value, label):
        # Outer rim
        pygame.draw.circle(screen, (30, 35, 40), (cx, cy), radius)
        pygame.draw.circle(screen, (150, 155, 160), (cx, cy), radius, 4)
        pygame.draw.circle(screen, (10, 15, 22), (cx, cy), radius - 4)
        
        # Draw tick marks
        for i in range(9):
            frac = i / 8.0
            angle = 3.14159 * (1.25 - frac * 1.5) # Arc from 225 to -45 degrees
            inner = (cx + cos(angle) * (radius - 12), cy - sin(angle) * (radius - 12))
            outer = (cx + cos(angle) * (radius - 4), cy - sin(angle) * (radius - 4))
            color = (239, 68, 68) if i >= 6 else (255, 255, 255) # Red zone
            pygame.draw.line(screen, color, inner, outer, 2)
            
        # Draw needle pointing at current value
        val_frac = clamp(value / max_value, 0.0, 1.0)
        needle_angle = 3.14159 * (1.25 - val_frac * 1.5)
        needle_end = (cx + cos(needle_angle) * (radius - 8), cy - sin(needle_angle) * (radius - 8))
        pygame.draw.line(screen, (220, 38, 38), (cx, cy), needle_end, 3)
        pygame.draw.circle(screen, (220, 38, 38), (cx, cy), 6)
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 3)
        
        # Draw label
        lbl_font = self.make_font(14)
        lbl_text = lbl_font.render(label, True, (255, 255, 255))
        screen.blit(lbl_text, lbl_text.get_rect(center=(cx, cy + radius - 20)))

    def draw_nos_bottle(self, screen, x, y):
        # Blue bottle body
        rect = pygame.Rect(x, y, 22, 44)
        pygame.draw.rect(screen, (37, 99, 235), rect, border_radius=4)
        pygame.draw.rect(screen, (255, 255, 255), rect, width=1, border_radius=4)
        
        # Bottle neck
        pygame.draw.rect(screen, (156, 163, 175), (x + 7, y - 6, 8, 6))
        # Silver cap
        pygame.draw.circle(screen, (156, 163, 175), (x + 11, y - 8), 5)
        # NOS label
        lbl_font = pygame.font.SysFont("arial", 9, bold=True)
        lbl = lbl_font.render("NOS", True, (255, 255, 255))
        screen.blit(lbl, lbl.get_rect(center=(x + 11, y + 22)))

    def draw_pause_button(self, screen, x, y):
        pygame.draw.rect(screen, (255, 255, 255), (x, y, 8, 24), border_radius=2)
        pygame.draw.rect(screen, (255, 255, 255), (x + 14, y, 8, 24), border_radius=2)

    def render_game_over(self, screen: pygame.Surface, result) -> None:
        """Render the game over summary card."""

        panel = pygame.Rect(int(WIDTH * 0.5 - 230), int(HEIGHT * 0.2), 460, 380)
        pygame.draw.rect(screen, UI_PANEL, panel, border_radius=28)
        self.draw_title(screen, "Game Over", panel.centerx, panel.top + 54)
        font = self.make_font(24)
        lines = [
            f"Distance: {result.distance} m",
            f"Coins: {result.coins}",
            f"Score: {result.score}",
            "Press R to retry",
        ]
        for index, line in enumerate(lines):
            text = font.render(line, True, TEXT_MAIN)
            screen.blit(text, text.get_rect(center=(panel.centerx, panel.top + 150 + index * 44)))

    def render_settings(self, screen: pygame.Surface) -> None:
        """Render a basic settings screen."""

        panel = pygame.Rect(int(WIDTH * 0.5 - 230), int(HEIGHT * 0.18), 460, 360)
        pygame.draw.rect(screen, UI_PANEL, panel, border_radius=28)
        self.draw_title(screen, "Settings", panel.centerx, panel.top + 52)
        font = self.make_font(24)
        small = self.make_font(18)
        mute_text = "Muted" if self.game.sound.muted else "Sound On"
        screen.blit(font.render(mute_text, True, TEXT_MAIN), (panel.left + 36, panel.top + 150))
        screen.blit(small.render("Click to toggle audio. Use ESC to return.", True, TEXT_MUTED), (panel.left + 36, panel.top + 182))
        pygame.draw.rect(screen, ACCENT_BLUE, pygame.Rect(panel.left + 36, panel.top + 240, 160, 48), border_radius=14)
        pygame.draw.rect(screen, ACCENT_RED, pygame.Rect(panel.left + 216, panel.top + 240, 160, 48), border_radius=14)
        screen.blit(font.render("Toggle", True, BLACK), (panel.left + 73, panel.top + 249))
        screen.blit(font.render("Back", True, BLACK), (panel.left + 264, panel.top + 249))

    def handle_settings_click(self, pos) -> None:
        """Handle clicks on the settings screen controls."""

        base_x = int(WIDTH * 0.5 - 230)
        base_y = int(HEIGHT * 0.18)
        toggle = pygame.Rect(base_x + 36, base_y + 240, 160, 48)
        back = pygame.Rect(base_x + 216, base_y + 240, 160, 48)
        if toggle.collidepoint(pos):
            self.game.sound.toggle_mute()
            self.game.save_progress()
        elif back.collidepoint(pos):
            self.game.open_menu()

    def draw_panel(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        """Draw a rounded UI panel."""

        shadow = rect.move(0, 6)
        pygame.draw.rect(screen, (0, 0, 0, 80), shadow, border_radius=20)
        pygame.draw.rect(screen, UI_PANEL, rect, border_radius=20)
        pygame.draw.rect(screen, UI_BORDER, rect, width=1, border_radius=20)

    def draw_bar(self, screen: pygame.Surface, x: int, y: int, width: int, height: int, fraction: float, color: Tuple[int, int, int]) -> None:
        """Draw a filled progress bar."""

        fraction = clamp(fraction, 0.0, 1.0)
        pygame.draw.rect(screen, UI_PANEL_SOFT, (x, y, width, height), border_radius=8)
        pygame.draw.rect(screen, color, (x, y, int(width * fraction), height), border_radius=8)

    def draw_button(self, screen: pygame.Surface, button: MenuButton) -> None:
        """Draw one menu button with hover scaling."""

        hover_scale = 1.0 + button.hover * 0.03
        rect = button.rect.inflate(int(button.rect.width * (hover_scale - 1.0)), int(button.rect.height * (hover_scale - 1.0)))
        pygame.draw.rect(screen, (0, 0, 0, 70), rect.move(0, 5), border_radius=16)
        pygame.draw.rect(screen, ACCENT_BLUE if button.action != "exit" else ACCENT_RED, rect, border_radius=16)
        pygame.draw.rect(screen, UI_BORDER, rect, width=1, border_radius=16)
        label = self.make_font(26).render(button.label, True, BLACK)
        screen.blit(label, label.get_rect(center=rect.center))

    def draw_title(self, screen: pygame.Surface, text: str, center_x: int, top_y: int) -> None:
        """Draw a large menu title."""

        font = self.make_font(64)
        title = font.render(text, True, TEXT_MAIN)
        screen.blit(title, title.get_rect(center=(center_x, top_y)))

    def make_font(self, size: int) -> pygame.font.Font:
        """Create a bold UI font."""

        return pygame.font.SysFont("arial", size, bold=True)
