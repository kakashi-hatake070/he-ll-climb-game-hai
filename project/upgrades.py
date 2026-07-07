"""Vehicle upgrade tables and progression logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from settings import BASE_UPGRADE_COST, MAX_UPGRADE_LEVEL, UPGRADE_COST_MULTIPLIER, clamp, upgrade_cost


@dataclass
class UpgradeManager:
    """Hold upgrade levels and derived multipliers."""

    save_data: Dict[str, int | float | bool]
    engine_level: int = 0
    suspension_level: int = 0
    tires_level: int = 0
    fuel_tank_level: int = 0
    boost_level: int = 0
    weight_reduction_level: int = 0

    def __post_init__(self) -> None:
        self.engine_level = int(self.save_data.get("engine_level", 0))
        self.suspension_level = int(self.save_data.get("suspension_level", 0))
        self.tires_level = int(self.save_data.get("tires_level", 0))
        self.fuel_tank_level = int(self.save_data.get("fuel_tank_level", 0))
        self.boost_level = int(self.save_data.get("boost_level", 0))
        self.weight_reduction_level = int(self.save_data.get("weight_reduction_level", 0))

    @property
    def engine_multiplier(self) -> float:
        return 1.0 + self.engine_level * 0.08

    @property
    def suspension_multiplier(self) -> float:
        return 1.0 + self.suspension_level * 0.06

    @property
    def grip_multiplier(self) -> float:
        return 1.0 + self.tires_level * 0.07

    @property
    def fuel_efficiency_multiplier(self) -> float:
        return 1.0 + self.fuel_tank_level * 0.06

    @property
    def brake_multiplier(self) -> float:
        return 1.0 + self.tires_level * 0.04

    @property
    def weight_multiplier(self) -> float:
        return max(0.68, 1.0 - self.weight_reduction_level * 0.03)

    def cost_for(self, level: int) -> int:
        """Return the next upgrade cost for a level."""

        return upgrade_cost(BASE_UPGRADE_COST, level)

    def can_buy(self, level: int) -> bool:
        """Return True if the level is still available."""

        return level < MAX_UPGRADE_LEVEL

    def apply_purchase(self, name: str) -> None:
        """Increment a specific upgrade by one level."""

        value = getattr(self, name)
        setattr(self, name, int(clamp(value + 1, 0, MAX_UPGRADE_LEVEL)))
