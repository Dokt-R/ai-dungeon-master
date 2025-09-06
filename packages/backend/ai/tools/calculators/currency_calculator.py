"""
Currency Calculator
This module provides definitions and utility functions for handling D&D 5e currency.
"""

from enum import Enum
from typing import TypedDict


class CoinType(Enum):
    """D&D 5e coin denominations"""

    COPPER = "cp"
    SILVER = "sp"
    ELECTRUM = "ep"
    GOLD = "gp"
    PLATINUM = "pp"


COIN_CONVERSIONS = {
    CoinType.COPPER: 0.01,
    CoinType.SILVER: 0.1,
    CoinType.ELECTRUM: 0.5,
    CoinType.GOLD: 1.0,
    CoinType.PLATINUM: 10.0,
}


class Wallet(TypedDict):
    """Represents a character's currency holdings."""

    cp: int
    sp: int
    ep: int
    gp: int
    pp: int


COIN_WEIGHT_PER_COIN = 1 / 50  # 50 coins weigh one pound


def calculate_total_value_in_gp(wallet: Wallet) -> float:
    """Calculates the total value of a wallet in Gold Pieces."""
    total_gp = 0.0
    total_gp += wallet.get("cp", 0) * COIN_CONVERSIONS[CoinType.COPPER]
    total_gp += wallet.get("sp", 0) * COIN_CONVERSIONS[CoinType.SILVER]
    total_gp += wallet.get("ep", 0) * COIN_CONVERSIONS[CoinType.ELECTRUM]
    total_gp += wallet.get("gp", 0) * COIN_CONVERSIONS[CoinType.GOLD]
    total_gp += wallet.get("pp", 0) * COIN_CONVERSIONS[CoinType.PLATINUM]
    return total_gp


def calculate_coin_weight(wallet: Wallet) -> float:
    """Calculates the total weight of coins in a wallet."""
    total_coins = sum(wallet.values())
    return total_coins * COIN_WEIGHT_PER_COIN
