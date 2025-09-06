"""
State definitions for AI Dungeon Master.

This module provides all standardized state definitions and data structures used
throughout the AI Dungeon Master system with full D&D 5e integration.
"""

# Base D&D 5e schemas and enums
# Action resolution workflow schemas
from .action_resolution_state import (
    ActionResolutionState,
    ParsedIntent,
)
from .base_state import (
    ActionResult,
    Attack,
    Character,
    Condition,
    DamageType,
    Item,
    calculate_modifier,
)
from .combat_state import CombatParticipant, CombatState, Effect

# Environment state schemas
from .environment_state import (
    DynamicRoom,
    EnvironmentalEffect,
    InteractionType,
    InteractiveObject,
    TacticalRoom,
    TerrainType,
)

# Complete game world schemas
from .game_state import (
    GameObject,
    GameState,
    Room,
    create_character,
    create_micro_adventure_state,
)

__all__ = [
    # Base D&D systems
    "DamageType",
    "Condition",
    "Attack",
    "Item",
    "Character",
    "ActionResult",
    "calculate_modifier",
    # Action resolution
    "ActionResolutionState",
    "ParsedIntent",
    # Game world
    "GameObject",
    "Room",
    "GameState",
    "create_micro_adventure_state",
    "create_character",
    # Environment State
    "InteractionType",
    "InteractiveObject",
    "EnvironmentalEffect",
    "DynamicRoom",
    "TerrainType",
    "TacticalRoom",
    # Combat
    "CombatParticipant",
    "Effect",
    "CombatState",
]
