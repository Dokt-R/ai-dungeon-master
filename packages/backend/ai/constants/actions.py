"""
Action Constants and Definitions

Standardized action keywords, types, and routing mappings for the AI Dungeon Master system.
These replace hardcoded dictionaries and provide consistent action handling across all nodes.

This module centralizes all action-related constants to support the modular AI node architecture:
- Action keyword sets for parsing
- Target category definitions
- Routing mappings from actions to nodes
- Social skill mappings
- Dialogue processing constants
"""

from typing import Dict, List, Set

# Action Type Categories
ACTION_TYPES = {
    "COMBAT": ["attack", "defend", "cast"],
    "EXPLORATION": ["move", "search", "investigate", "examine", "open", "unlock", "look"],
    "INTERACTION": ["use", "take", "talk", "persuade", "intimidate", "deceive", "speak", "say"]
}

# Standardized keyword sets for intent parsing
COMBAT_KEYWORDS: Set[str] = {
    "attack", "strike", "hit", "fight", "swing", "stab", "slash",
    "defend", "cast", "spell", "shoot", "bash", "charge"
}

EXPLORATION_KEYWORDS: Set[str] = {
    "move", "search", "investigate", "examine", "inspect", "look",
    "open", "unlock", "enter", "leave", "go", "walk", "crawl"
}

INTERACTION_KEYWORDS: Set[str] = {
    "use", "take", "get", "grab", "pick", "talk", "speak", "say",
    "persuade", "intimidate", "deceive", "trick", "charm",
    "activate", "consume", "drink", "eat", "wear", "equip"
}

# Standard target lists by game context | #! TO BE ENHANCED WITH SRD MONSTERS
COMBAT_TARGETS: List[str] = [
    "goblin", "orc", "dragon", "enemy", "monster", "creature",
    "bandit", "guard", "soldier", "beast", "undead"
]

INTERACTION_TARGETS: List[str] = [
    "chest", "door", "key", "potion", "sword", "shield",
    "armor", "weapon", "item", "lever", "button", "switch",
    "lock", "trap", "lever", "gate", "barrel", "crate"
]

EXPLORATION_TARGETS: List[str] = [
    "room", "area", "corridor", "chamber", "hall", "cave",
    "tunnel", "passage", "entrance", "exit", "floor", "ceiling",
    "walls", "ground", "surroundings", "environment"
]

# Routing map - action_type to node mapping
ROUTE_MAPPING: Dict[str, str] = {
    # Combat actions
    "attack": "combat_node",
    "defend": "combat_node",
    "cast": "combat_node",

    # Exploration actions
    "move": "exploration_node",
    "search": "exploration_node",
    "investigate": "exploration_node",
    "examine": "exploration_node",
    "open": "exploration_node",
    "unlock": "exploration_node",
    "look": "exploration_node",

    # Interaction actions
    "use": "interaction_node",
    "take": "interaction_node",
    "talk": "interaction_node",
    "speak": "interaction_node",
    "say": "interaction_node",
    "persuade": "interaction_node",
    "intimidate": "interaction_node",
    "deceive": "interaction_node",
    "grab": "interaction_node",
    "pick": "interaction_node",
    "activate": "interaction_node"
}

# Action-specific target mapping
ACTION_TARGET_MAPPING = {
    "attack": COMBAT_TARGETS,
    "strike": COMBAT_TARGETS,
    "hit": COMBAT_TARGETS,
    "fight": COMBAT_TARGETS,
    "swing": COMBAT_TARGETS,
    "defend": ["defense", "position", "area"],

    "use": INTERACTION_TARGETS,
    "take": INTERACTION_TARGETS,
    "grab": INTERACTION_TARGETS,
    "pick": INTERACTION_TARGETS,
    "activate": INTERACTION_TARGETS,

    "talk": ["goblin", "npc", "guard", "merchant", "person"],
    "speak": ["goblin", "npc", "guard", "merchant", "person"],
    "say": ["goblin", "npc", "guard", "merchant", "person"],
    "persuade": ["goblin", "npc", "guard", "merchant", "person"],
    "intimidate": ["goblin", "npc", "guard", "merchant", "person"],
    "deceive": ["goblin", "npc", "guard", "merchant", "person"],

    "examine": INTERACTION_TARGETS + EXPLORATION_TARGETS,
    "inspect": INTERACTION_TARGETS + EXPLORATION_TARGETS,
    "look": INTERACTION_TARGETS + EXPLORATION_TARGETS,
    "open": INTERACTION_TARGETS,
    "unlock": INTERACTION_TARGETS,
    "search": EXPLORATION_TARGETS,
    "investigate": EXPLORATION_TARGETS
}

# Dialogue keywords for enhanced conversation extraction
DIALOGUE_KEYWORDS: Set[str] = {
    "say", "speak", "talk", "tell", "ask", "yell", "whisper",
    "shout", "scream", "call", "reply", "respond", "answer"
}

# Social skills mapping for D&D compatibility
SOCIAL_SKILL_MAPPING = {
    "persuade": "persuasion",
    "intimidate": "intimidation",
    "deceive": "deception",
    "trick": "deception",
    "charm": "persuasion",
    "diplomacy": "persuasion",
    "bluff": "deception"
}

# Item interaction types
ITEM_INTERACTION_TYPES = {
    "CONSUMABLE": ["drink", "eat", "consume", "quaff"],
    "EQUIPMENT": ["wear", "wield", "equip", "don"],
    "FUNCTIONAL": ["use", "activate", "trigger", "pull"],
    "KEY": ["unlock", "open", "insert", "turn"]
}