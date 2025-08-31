"""
Base State Definitions

This module contains fundamental types and enums used across all game state modules.
These provide the standardized building blocks for D&D 5e mechanics.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field

from packages.backend.ai.tools.calculators.currency_calculator import Wallet, calculate_coin_weight


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


class InteractionType(Enum):
    """Defines extensible types of interactions with objects or the environment."""
    EXAMINE = "examine"
    USE = "use"
    ATTACK = "attack"
    PUSH = "push"
    PULL = "pull"
    ACTIVATE = "activate"
    COMBINE = "combine"
    LOOK = "look"
    TAKE = "take"
    OPEN = "open"
    CLOSE = "close"
    UNLOCK = "unlock"
    LOCK = "lock"


class Attack(TypedDict):
    """Standardized attack definition"""
    name: str
    bonus: int  # Attack bonus (ability mod + proficiency + magic)
    damage: str  # Dice notation (e.g., "1d8+2")
    damage_type: str  # Use DamageType enum value
    range: int  # Range in feet (5 for melee, higher for ranged)


class Item(BaseModel):
    """Standardized item definition"""
    name: str
    type: str = Field(..., description="e.g., weapon, armor, consumable, key, misc")
    weight: float = Field(..., ge=0)
    value: int = Field(..., ge=0, description="Value in copper pieces")
    description: str
    source: str = Field("SRD", description="Can be SRD, Homebrew or other")
    
    # Gameplay properties
    quantity: int = Field(1, ge=1)
    is_stackable: bool = False
    rarity: str = Field("common", description="e.g., common, uncommon, rare, legendary")
    requires_attunement: bool = False
    
    # Functional properties
    effects: Dict[str, Any] = Field(default_factory=dict, description="e.g., {'passive': {'ac_bonus': 1}, 'on_use': {'heal': '1d4'}}")
    interactions: Dict[InteractionType, Dict[str, Any]] = Field(default_factory=dict, description="How the item can be used")
    properties: Dict[str, Any] = Field(default_factory=dict, description="For miscellaneous data")
    
    # State
    equipped: Optional[bool] = False




class Character(BaseModel):
    """Comprehensive character/NPC definition following D&D 5e rules"""
    name: str
    hp: int
    max_hp: int
    ac: int  # Armor Class
    speed: int  # Movement speed in feet

    # Ability scores (1-30)
    strength: int = Field(..., ge=1, le=30)
    dexterity: int = Field(..., ge=1, le=30)
    constitution: int = Field(..., ge=1, le=30)
    intelligence: int = Field(..., ge=1, le=30)
    wisdom: int = Field(..., ge=1, le=30)
    charisma: int = Field(..., ge=1, le=30)

    # Combat
    attacks: List[Attack] = Field(default_factory=list)
    proficiency_bonus: int = 2

    # Status
    conditions: List[Condition] = Field(default_factory=list)
    is_alive: bool = True
    is_hostile: bool = False

    # Inventory
    inventory: List[Item] = Field(default_factory=list)
    equipped_items: Dict[str, Item] = Field(default_factory=dict)
    wallet: Wallet = Field(default_factory=lambda: {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0})

    # Resources
    spell_slots: Optional[Dict[int, int]] = None
    hit_dice: Optional[str] = None
    hit_dice_remaining: Optional[int] = None

    @property
    def strength_mod(self) -> int:
        return calculate_modifier(self.strength)

    @property
    def dexterity_mod(self) -> int:
        return calculate_modifier(self.dexterity)

    @property
    def constitution_mod(self) -> int:
        return calculate_modifier(self.constitution)

    @property
    def intelligence_mod(self) -> int:
        return calculate_modifier(self.intelligence)

    @property
    def wisdom_mod(self) -> int:
        return calculate_modifier(self.wisdom)

    @property
    def charisma_mod(self) -> int:
        return calculate_modifier(self.charisma)

    @property
    def initiative_modifier(self) -> int:
        return self.dexterity_mod

    def get_total_weight(self) -> float:
        """Calculates the total weight of all items and coins."""
        item_weight = sum(item.get("weight", 0.0) * item.get("quantity", 1) for item in self.inventory)
        coin_weight = calculate_coin_weight(self.wallet)
        return item_weight + coin_weight

    def to_dict(self) -> Dict[str, Any]:
        """
        Returns a dictionary representation of the character, including
        computed properties for LangGraph compatibility.
        """
        data = self.model_dump()
        data["strength_mod"] = self.strength_mod
        data["dexterity_mod"] = self.dexterity_mod
        data["constitution_mod"] = self.constitution_mod
        data["intelligence_mod"] = self.intelligence_mod
        data["wisdom_mod"] = self.wisdom_mod
        data["charisma_mod"] = self.charisma_mod
        data["initiative_modifier"] = self.initiative_modifier
        return data


@dataclass
class ActionResult:
    """Standardized result structure for node operations"""
    success: bool
    description: str
    state_changes: Dict[str, Any]
    resolution_details: Optional[Dict[str, Any]] = None



@dataclass
class Position:
    """Represents a 3D position in the game world."""
    x: int
    y: int
    z: int


class EnvironmentalEffect(TypedDict):
    """Represents an environmental effect."""
    name: str
    description: str
    effect_type: str  # e.g., "magical", "weather", "hazard"
    duration: int  # in rounds, -1 for permanent
    area_of_effect: Dict[str, Any]  # e.g., {"shape": "sphere", "radius": 10}


class InteractiveObject(TypedDict):
    """Represents an object in the environment that can be interacted with."""
    name: str
    description: str
    position: Position
    is_interactive: bool
    is_movable: bool
    properties: Dict[str, Any]  # e.g., {"locked": true, "key_id": "key_to_chest"}


class Room(TypedDict):
    """Represents a single location in the game world."""
    name: str
    description: str
    dimensions: Dict[str, int]  # e.g., {"width": 20, "length": 30, "height": 10}
    terrain: str  # TerrainType enum value
    objects: List[InteractiveObject]
    characters: List[str]  # List of character names/IDs
    environmental_effects: List[EnvironmentalEffect]
    exits: Dict[str, str]  # e.g., {"north": "room_id_2"}


def calculate_modifier(score: int) -> int:
    """Calculate D&D 5e ability modifier from ability score."""
    return (score - 10) // 2
