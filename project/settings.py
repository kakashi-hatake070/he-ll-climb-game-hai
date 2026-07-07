"""Game-wide settings and tuning constants for Hill Climb Clone.

This module keeps all shared values in one place so gameplay systems can
import the same numbers without duplicating magic constants.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
SOUNDS_DIR = ASSETS_DIR / "sounds"
FONTS_DIR = ASSETS_DIR / "fonts"
SAVE_FILE = PROJECT_ROOT / "save.json"

# ---------------------------------------------------------------------------
# Window / rendering
# ---------------------------------------------------------------------------

WINDOW_TITLE = "Hill Climb Clone"
WIDTH = 1280
HEIGHT = 720
FPS = 60
TARGET_DT = 1.0 / FPS

# ---------------------------------------------------------------------------
# World / camera
# ---------------------------------------------------------------------------

CAMERA_LERP_X = 0.08
CAMERA_LERP_Y = 0.08
CAMERA_SHAKE_DECAY = 10.0
CAMERA_SHAKE_INTENSITY = 14.0
PARALLAX_SKY = 0.08
PARALLAX_MOUNTAINS = 0.18
PARALLAX_TREES = 0.35
PARALLAX_BUSHES = 0.55

# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------

GRAVITY = 2200.0
GROUND_FRICTION = 0.92
AIR_DRAG = 0.998
MAX_UPRIGHT_ANGLE = 1.45
HARD_CRASH_ANGULAR_VELOCITY = 6.2
HARD_LANDING_SPEED = 980.0
WHEEL_CONTACT_BAND = 4.0
WHEEL_SUSPENSION_STIFFNESS = 0.78
WHEEL_SUSPENSION_DAMPING = 0.18
BODY_STABILIZE_FORCE = 1.45

# ---------------------------------------------------------------------------
# Vehicle tuning
# ---------------------------------------------------------------------------

BASE_VEHICLE_MASS = 230.0
BASE_ENGINE_POWER = 2800.0
BASE_BRAKE_FORCE = 0.75
BASE_GRIP = 1.0
BASE_SUSPENSION = 1.0
BASE_FUEL_EFFICIENCY = 1.0
BASE_WEIGHT = 1.0
BOOST_FORCE = 3800.0
BOOST_FUEL_COST = 16.0

# Upgrade caps.
MAX_UPGRADE_LEVEL = 20
BASE_UPGRADE_COST = 120
UPGRADE_COST_MULTIPLIER = 1.25

# ---------------------------------------------------------------------------
# Gameplay
# ---------------------------------------------------------------------------

DISTANCE_SCALE = 10.0
COIN_SPAWN_MIN_GAP = 160.0
COIN_SPAWN_MAX_GAP = 420.0
FUEL_SPAWN_MIN_GAP = 500.0
FUEL_SPAWN_MAX_GAP = 900.0
CHUNK_SIZE = 320
CHUNK_BUFFER_AHEAD = 3000
CHUNK_BUFFER_BEHIND = 1000
MAX_ACTIVE_PARTICLES = 1200

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

KEY_ACCELERATE = "right"
KEY_BRAKE = "left"
KEY_TILT_LEFT = "a"
KEY_TILT_RIGHT = "d"
KEY_BOOST = "space"
KEY_RESTART = "r"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

WHITE = (245, 248, 252)
BLACK = (10, 15, 22)
SKY_DAY_TOP = (122, 197, 255)
SKY_DAY_BOTTOM = (214, 241, 255)
SKY_NIGHT_TOP = (14, 22, 48)
SKY_NIGHT_BOTTOM = (25, 40, 72)
UI_PANEL = (18, 27, 44)
UI_PANEL_SOFT = (27, 39, 61)
UI_BORDER = (255, 255, 255)
TEXT_MAIN = (247, 250, 252)
TEXT_MUTED = (194, 205, 218)
ACCENT_GREEN = (73, 214, 130)
ACCENT_RED = (255, 104, 132)
ACCENT_BLUE = (96, 165, 250)
ACCENT_GOLD = (249, 195, 67)
ACCENT_SILVER = (205, 214, 226)
ACCENT_DIAMOND = (114, 230, 255)
GROUND_GREEN = (63, 143, 72)
GROUND_DARK = (39, 103, 52)
DUST = (214, 190, 162)
SMOKE = (164, 172, 183)
SPARK = (255, 218, 104)
BOOST = (255, 129, 62)

# ---------------------------------------------------------------------------
# Save defaults
# ---------------------------------------------------------------------------

DEFAULT_SAVE = {
    "coins": 0,
    "best_distance": 0,
    "best_score": 0,
    "engine_level": 0,
    "suspension_level": 0,
    "tires_level": 0,
    "fuel_tank_level": 0,
    "boost_level": 0,
    "weight_reduction_level": 0,
    "sound_volume": 0.8,
    "muted": False,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a numeric value into a fixed range."""

    return max(minimum, min(maximum, value))


def lerp(start: float, end: float, amount: float) -> float:
    """Linearly interpolate between two values."""

    return start + (end - start) * amount


def ease_out_cubic(amount: float) -> float:
    """Return a smooth easing curve for menu and UI animation."""

    amount = clamp(amount, 0.0, 1.0)
    return 1.0 - (1.0 - amount) ** 3


def format_distance(distance_value: float) -> str:
    """Format a world distance value for display."""

    return f"DISTANCE: {int(distance_value)}m"


def format_coin_count(coin_count: int) -> str:
    """Format the coin count for display."""

    return f"COINS: {coin_count}"


def upgrade_cost(base_cost: int, level: int) -> int:
    """Compute the upgrade price for a given level."""

    return int(round(base_cost * (UPGRADE_COST_MULTIPLIER ** level)))
