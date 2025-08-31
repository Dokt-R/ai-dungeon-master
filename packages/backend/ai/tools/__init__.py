"""
Calculator tools for D&D operations.
"""

from .dice_roller import (
    DiceRoller,
    DiceType,
    AdvantageType,
    DiceRoll,
    RollResult,
    roll,
    roll_stats
)

from .calculators.currency_calculator import (
    CoinType,
    Wallet,
    COIN_CONVERSIONS,
    COIN_WEIGHT_PER_COIN,
    calculate_total_value_in_gp,
    calculate_coin_weight,
)

__all__ = [
    "DiceRoller",
    "DiceType", 
    "AdvantageType",
    "DiceRoll",
    "RollResult",
    "roll",
    "roll_stats",
    "CoinType",
    "Wallet",
    "COIN_CONVERSIONS",
    "COIN_WEIGHT_PER_COIN",
    "calculate_total_value_in_gp",
    "calculate_coin_weight",
]