"""
Base State Definitions

This module contains fundamental types and enums used across all game state modules.
These provide the standardized building blocks for D&D 5e mechanics.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class DamageType(Enum):
    """D&D 5e damage types"""
    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    ACID = "acid"
    POISON = "poison"
    PSYCHIC = "psychic"
    NECROTIC = "necrotic"
    RADIANT = "radiant"
    LIGHTNING = "lightning"
    THUNDER = "thunder"
    FORCE = "force"


class Condition(Enum):
    """D&D 5e conditions"""
    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"


class Attack(TypedDict):
    """Standardized attack definition"""
    name: str
    bonus: int  # Attack bonus (ability mod + proficiency + magic)
    damage: str  # Dice notation (e.g., "1d8+2")
    damage_type: str  # Use DamageType enum value
    range: int  # Range in feet (5 for melee, higher for ranged)


class Item(TypedDict):
    """Standardized item definition"""
    name: str
    type: str  # weapon, armor, consumable, key, misc
    weight: float
    value: int  # Value in copper pieces
    properties: Dict[str, Any]
    description: str
    equipped: Optional[bool]


class Character(TypedDict):
    """Comprehensive character/NPC definition following D&D 5e rules"""
    name: str
    hp: int
    max_hp: int
    ac: int  # Armor Class
    speed: int  # Movement speed in feet

    # Ability scores (1-20)
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int

    # Derived modifiers ((-5) to (+5) typically)
    strength_mod: int
    dexterity_mod: int
    constitution_mod: int
    intelligence_mod: int
    wisdom_mod: int
    charisma_mod: int

    # Combat
    attacks: List[Attack]
    proficiency_bonus: int  # 2 for levels 1-4, scales up
    initiative_modifier: int  # Usually dex_mod

    # Status
    conditions: List[str]  # Use Condition enum values
    is_alive: bool
    is_hostile: bool

    # Inventory (player only)
    inventory: Optional[List[Item]]
    equipped_items: Optional[Dict[str, Item]]  # slot -> item

    # Resources (magical characters)
    spell_slots: Optional[Dict[int, int]]  # level -> remaining slots
    hit_dice: Optional[str]  # e.g., "1d8+1"
    hit_dice_remaining: Optional[int]


@dataclass
class ActionResult:
    """Standardized result structure for node operations"""
    success: bool
    description: str
    state_changes: Dict[str, Any]
    resolution_details: Optional[Dict[str, Any]] = None


def calculate_modifier(score: int) -> int:
    """Calculate D&D 5e ability modifier from ability score."""
    return (score - 10) // 2