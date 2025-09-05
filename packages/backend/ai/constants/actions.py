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
    "attack": "combat_subgraph",
    "cast": "combat_subgraph",
    "combat": "combat_subgraph",
    "defend": "combat_subgraph",

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
    "activate": "interaction_node",
    "interaction": "interaction_node"
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

from enum import Enum

class ActionType(Enum):
    """Defines the main actions a character can take on their turn, based on the SRD."""
    ATTACK = "Attack with a weapon or an Unarmed Strike."
    DASH = "For the rest of the turn, give yourself extra movement equal to your Speed."
    DISENGAGE = "Your movement doesn’t provoke Opportunity Attacks for the rest of the turn."
    DODGE = "Until the start of your next turn, attack rolls against you have Disadvantage, and you make Dexterity saving throws with Advantage."
    HELP = "Help another creature’s ability check or attack roll, or administer first aid."
    HIDE = "Make a Dexterity (Stealth) check."
    INFLUENCE = "Make a Charisma (Deception, Intimidation, Performance, or Persuasion) or Wisdom (Animal Handling) check to alter a creature’s attitude."
    MAGIC = "Cast a spell, use a magic item, or use a magical feature."
    READY = "Prepare to take an action in response to a trigger you define."
    SEARCH = "Make a Wisdom (Insight, Medicine, Perception, or Survival) check."
    STUDY = "Make an Intelligence (Arcana, History, Investigation, Nature, or Religion) check."
    UTILIZE = "Use a nonmagical object."


class SkillType(Enum):
    """Defines the skills a character can use, based on the SRD."""
    ACROBATICS = "Stay on your feet in a tricky situation, or perform an acrobatic stunt."
    ANIMAL_HANDLING = "Calm or train an animal, or get an animal to behave in a certain way."
    ARCANA = "Recall lore about spells, magic items, and the planes of existence."
    ATHLETICS = "Jump farther than normal, stay afloat in rough water, or break something."
    DECEPTION = "Tell a convincing lie, or wear a disguise convincingly."
    HISTORY = "Recall lore about historical events, people, nations, and cultures."
    INSIGHT = "Discern a person’s mood and intentions."
    INTIMIDATION = "Awe or threaten someone into doing what you want."
    INVESTIGATION = "Find obscure information in books, or deduce how something works."
    MEDICINE = "Diagnose an illness, or determine what killed the recently slain."
    NATURE = "Recall lore about terrain, plants, animals, and weather."
    PERCEPTION = "Using a combination of senses, notice something that’s easy to miss."
    PERFORMANCE = "Act, tell a story, perform music, or dance."
    PERSUASION = "Honestly and graciously convince someone of something."
    RELIGION = "Recall lore about gods, religious rituals, and holy symbols."
    SLEIGHT_OF_HAND = "Pick a pocket, conceal a handheld object, or perform legerdemain."
    STEALTH = "Escape notice by moving quietly and hiding behind things."
    SURVIVAL = "Follow tracks, forage, find a trail, or avoid natural hazards."