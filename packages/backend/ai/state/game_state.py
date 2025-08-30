"""
Game State Definitions

This module contains standardized game state structures following D&D 5e mechanics.
Replaces generic dictionaries with proper TypedDict structures for type safety and consistency.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

from .base_state import Attack, Character, Item, calculate_modifier


class GameObject(TypedDict):
    """Interactive object in the game world"""
    name: str
    description: str
    state: Dict[str, Any]  # Flexible state (locked, open, hidden, etc.)
    interactions: List[str]  # Available interactions
    contains: Optional[List[Item]]  # For containers


class Room(TypedDict):
    """Room/Location definition"""
    name: str
    description: str
    description_explored: Optional[str]  # After investigation
    exits: Dict[str, str]  # direction -> room_id
    objects: List[GameObject]
    items: List[Item]  # Items on the ground
    npcs: List[str]  # NPC ids present
    light_level: str  # bright, dim, darkness
    hazards: Optional[List[Dict[str, Any]]]
    explored: bool


class GameState(TypedDict):
    """Complete game state following D&D 5e standards"""
    # Core entities
    player: Character
    npcs: Dict[str, Character]  # id -> character
    current_room_id: str
    rooms: Dict[str, Room]  # id -> room

    # Game progress
    quest_flags: Dict[str, bool]
    completed_objectives: List[str]

    # Combat state (if in combat)
    in_combat: bool
    combat_order: Optional[List[str]]  # Turn order by character id
    current_turn: Optional[str]  # Character id

    # Narrative context
    recent_actions: List[str]  # Last N actions for context
    narrative_tone: str  # comedic, serious, dark, heroic

    # Meta
    turn_count: int
    session_id: str
    difficulty: str  # easy, medium, hard


# Legacy compatibility structures (for migration)
class GenericGameState(TypedDict):
    """Legacy structure for backward compatibility."""
    player: Dict[str, Any]
    npcs: List[Dict[str, Any]]
    room_description: str
    win_condition: Optional[str]
    current_room: str
    visited_rooms: List[str]


# Factory Functions
def create_character(
    name: str,
    hp: int,
    ac: int,
    abilities: Dict[str, int],
    attacks: List[Attack],
    is_hostile: bool = False
) -> Character:
    """Factory function to create a properly formatted character following D&D 5e rules."""
    return Character(
        name=name,
        hp=hp,
        max_hp=hp,
        ac=ac,
        speed=30,  # Standard human speed

        strength=abilities.get("strength", 10),
        dexterity=abilities.get("dexterity", 10),
        constitution=abilities.get("constitution", 10),
        intelligence=abilities.get("intelligence", 10),
        wisdom=abilities.get("wisdom", 10),
        charisma=abilities.get("charisma", 10),

        strength_mod=calculate_modifier(abilities.get("strength", 10)),
        dexterity_mod=calculate_modifier(abilities.get("dexterity", 10)),
        constitution_mod=calculate_modifier(abilities.get("constitution", 10)),
        intelligence_mod=calculate_modifier(abilities.get("intelligence", 10)),
        wisdom_mod=calculate_modifier(abilities.get("wisdom", 10)),
        charisma_mod=calculate_modifier(abilities.get("charisma", 10)),

        attacks=attacks,
        proficiency_bonus=2,  # Standard for levels 1-4
        initiative_modifier=calculate_modifier(abilities.get("dexterity", 10)),

        conditions=[],  # No conditions initially
        is_alive=True,
        is_hostile=is_hostile,

        inventory=[] if not is_hostile else None,
        equipped_items={} if not is_hostile else None,
        spell_slots=None,
        hit_dice="1d8" if not is_hostile else None,
        hit_dice_remaining=1 if not is_hostile else None
    )


def create_micro_adventure_state() -> GameState:
    """Create the initial state for the micro-adventure with standardized schemas."""

    player = create_character(
        name="Roric",
        hp=12,
        ac=14,
        abilities={
            "strength": 14, "dexterity": 13, "constitution": 14,
            "intelligence": 10, "wisdom": 12, "charisma": 8
        },
        attacks=[
            Attack(
                name="Shortsword",
                bonus=4,  # +2 str mod, +2 proficiency
                damage="1d6+2",
                damage_type="piercing",
                range=5
            )
        ]
    )

    # Add starting inventory items
    player["inventory"] = [
        Item(
            name="Sword",
            type="weapon",
            weight=3.0,
            value=50,
            properties={"weapon_type": "shortsword"},
            description="A simple iron shortsword.",
            equipped=False
        ),
        Item(
            name="Shield",
            type="armor",
            weight=6.0,
            value=30,
            properties={"armor": 2},
            description="A stout wooden shield.",
            equipped=False
        ),
        Item(
            name="Healing Potion",
            type="consumable",
            weight=0.5,
            value=50,
            properties={"healing": "2d4+2"},
            description="A red potion that restores health.",
            equipped=False
        ),
        Item(
            name="Key",
            type="key",
            weight=0.1,
            value=25,
            properties={},
            description="A simple iron key.",
            equipped=False
        )
    ]

    goblin = create_character(
        name="Goblin",
        hp=7,
        ac=15,
        abilities={
            "strength": 8, "dexterity": 14, "constitution": 10,
            "intelligence": 10, "wisdom": 8, "charisma": 8
        },
        attacks=[
            Attack(
                name="Scimitar",
                bonus=4,
                damage="1d6+2",
                damage_type="slashing",
                range=5
            )
        ],
        is_hostile=True
    )

    chest = GameObject(
        name="Iron Chest",
        description="A sturdy iron chest with an intricate lock.",
        state={"locked": True, "open": False, "trap_triggered": False},
        interactions=["examine", "unlock", "open", "search"],
        contains=[
            Item(
                name="Golden Key",
                type="key",
                weight=0.1,
                value=50,
                properties={"unlocks": "exit_door"},
                description="An ornate golden key that looks important.",
                equipped=False
            ),
            Item(
                name="Healing Potion",
                type="consumable",
                weight=0.5,
                value=50,
                properties={"healing": "2d4+2"},
                description="A red potion that restores health.",
                equipped=False
            )
        ]
    )

    # Add some items to the room for interaction testing
    room_items = [
        Item(
            name="Silver Coin",
            type="misc",
            weight=0.02,
            value=1,
            properties={},
            description="A shiny silver coin.",
            equipped=False
        ),
        Item(
            name="Iron Key",
            type="key",
            weight=0.1,
            value=10,
            properties={},
            description="A rusted iron key.",
            equipped=False
        )
    ]

    starting_room = Room(
        name="Damp Stone Chamber",
        description="A small, damp room with moss-covered stone walls. A single torch flickers on the wall, casting dancing shadows. You see a goblin standing guard near an iron chest in the corner. There are some items scattered on the floor.",
        description_explored="The room has scratch marks on the walls, as if something was dragged here. The chest sits on a slightly raised stone platform. A few items are scattered around the room.",
        exits={"north": "locked_exit"},
        objects=[chest],
        items=room_items,  # Add room items for pickup testing
        npcs=["goblin_1"],
        light_level="dim",
        hazards=None,
        explored=False
    )

    return GameState(
        player=player,
        npcs={"goblin_1": goblin},
        current_room_id="starting_room",
        rooms={"starting_room": starting_room},
        quest_flags={"has_key": False, "chest_opened": False, "goblin_defeated": False},
        completed_objectives=[],
        in_combat=False,
        combat_order=None,
        current_turn=None,
        recent_actions=[],
        narrative_tone="heroic",
        turn_count=0,
        session_id="std_micro_adventure",
        difficulty="medium"
    )