"""
State Definitions for AI Dungeon Master

This module contains all TypedDict state definitions and dataclasses used
throughout the AI Dungeon Master system, including action resolution,
combat, exploration, and social interactions.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict



# Game State Types
@dataclass
class GameEntity:
    """Base class for game entities (players, NPCs, monsters)."""
    name: str
    hp: int
    ac: int
    is_alive: bool = True


@dataclass
class Player(GameEntity):
    """Player character data."""
    level: int = 1
    attack: Optional[Dict[str, Any]] = None  # {'bonus': 3, 'damage': '1d8+1'}
    abilities: Optional[Dict[str, int]] = None


@dataclass
class NPC(GameEntity):
    """Non-player character data."""
    enemy: bool = True  # Hostile or friendly
    loot: Optional[List[str]] = None


# Generic Game State Structure
class GenericGameState(TypedDict):
    """Generic structure for any game state."""
    player: Dict[str, Any]
    npcs: List[Dict[str, Any]]
    room_description: str
    win_condition: Optional[str]
    current_room: str
    visited_rooms: List[str]


# Extension points for future states
# class CombatState(TypedDict):
#     """State for combat resolution."""
#     participants: List[Dict[str, Any]]
#     initiative_order: List[Dict[str, Any]]
#     current_turn: int
#     round_number: int
#     combat_active: bool
#
# class ExplorationState(TypedDict):
#     """State for exploration mechanics."""
#     current_location: str
#     discovered_locations: List[str]
#     hidden_items: List[Dict[str, Any]]
#
# class SocialState(TypedDict):
#     """State for social interactions."""
#     npc_relationships: Dict[str, int]
#     conversation_context: Optional[Dict[str, Any]]