"""
Enhanced Environment State System
This module provides a robust framework for managing the game's environment,
including interactive objects, environmental effects, dynamic rooms, and
tactical positioning. It is designed for immediate gameplay benefits and
future extensibility.
"""

import random
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from .base_state import InteractionType

# ============================================
# INTERACTIVE OBJECTS
# ============================================


class InteractiveObject(BaseModel):
    """
    Represents objects that respond to player actions, with multiple states
    and reactions.
    """

    name: str
    description: Dict[str, str]  # state -> description mapping
    current_state: str = "default"

    # Defines what happens when interacted with
    interactions: Dict[InteractionType, Dict[str, Any]] = Field(default_factory=dict)

    # Defines state transitions: {current_state: {trigger: next_state}}
    state_transitions: Dict[str, Dict[str, str]] = Field(default_factory=dict)

    # Gameplay-affecting properties
    properties: Dict[str, Any] = Field(default_factory=dict)

    def interact(self, action: InteractionType, **kwargs) -> Dict:
        """Processes an interaction and returns the result."""
        if action not in self.interactions:
            return {
                "success": False,
                "message": f"You can't {action.value} the {self.name}",
            }

        interaction = self.interactions[action]
        results = {"success": True, "effects": []}

        # Check requirements for the interaction
        if "requires" in interaction:
            for req_type, req_value in interaction["requires"].items():
                if req_type == "item" and req_value not in kwargs.get("inventory", []):
                    return {"success": False, "message": f"You need {req_value}"}
                elif req_type == "state" and self.current_state != req_value:
                    return {
                        "success": False,
                        "message": interaction.get("fail_message", "Nothing happens"),
                    }

        # Apply effects of the interaction
        if "effects" in interaction:
            results["effects"] = interaction["effects"]

        # Transition to a new state if defined
        if "next_state" in interaction:
            self.current_state = interaction["next_state"]
            results["new_description"] = self.description.get(self.current_state)

        return results


"""
# Example: Multi-state puzzle object
pressure_plate = InteractiveObject(
    name="Stone Pressure Plate",
    description={
        "default": "A slightly raised stone tile on the floor",
        "pressed": "The stone tile is depressed, and you hear grinding stone",
        "locked": "The tile is pressed down and won't budge"
    },
    current_state="default",
    interactions={
        InteractionType.PUSH: {
            "requires": {"weight": 150},  # pounds
            "effects": [{"type": "open_door", "target": "secret_door"}],
            "next_state": "pressed",
            "message": "The plate clicks down, and a section of wall slides open!"
        },
        InteractionType.EXAMINE: {
            "message": "You notice scratches suggesting it moves"
        }
    }
)
"""

# ============================================
# ENVIRONMENTAL EFFECTS
# ============================================


class EnvironmentalEffect(BaseModel):
    """
    Represents ongoing environmental effects that can trigger automatically,
    adding dynamic challenges and tactical depth.
    """

    name: str
    trigger_condition: str  # e.g., "turn_start", "on_enter", "every_n_turns"
    trigger_frequency: int = 1

    effect_type: str  # e.g., "damage", "condition", "spawn", "change_state"
    effect_data: Dict[str, Any]

    # Warnings to telegraph the effect to players
    warning_signs: List[str]
    current_warning_index: int = 0

    active: bool = True
    turns_until_trigger: int = 0

    def tick(self) -> Optional[Dict]:
        """Processes one turn, returning an effect if triggered."""
        if not self.active:
            return None

        self.turns_until_trigger -= 1

        # Provide a warning before the effect triggers
        if self.turns_until_trigger > 0 and self.current_warning_index < len(
            self.warning_signs
        ):
            warning = self.warning_signs[self.current_warning_index]
            self.current_warning_index += 1
            return {"type": "warning", "message": warning}

        # Trigger the effect
        if self.turns_until_trigger <= 0:
            self.turns_until_trigger = self.trigger_frequency
            self.current_warning_index = 0
            return {"type": "effect", "data": self.effect_data}

        return None


"""
# Example: Collapsing ceiling trap
ceiling_trap = EnvironmentalEffect(
    name="Collapsing Ceiling",
    trigger_condition="every_n_turns",
    trigger_frequency=3,
    effect_type="damage",
    effect_data={"damage": "2d6", "type": "bludgeoning", "save": "dex", "dc": 13},
    warning_signs=[
        "Dust falls from the ceiling...",
        "The ceiling groans ominously!",
        "CRACKS SPREAD ACROSS THE CEILING!"
    ],
    turns_until_trigger=3
)
"""

# ============================================
# DYNAMIC ROOMS
# ============================================


class DynamicRoom(BaseModel):
    """
    Represents rooms that change based on state and player actions, creating a
    more immersive and replayable experience.
    """

    name: str
    base_description: str

    # Conditional description additions: [(condition, description)]
    conditional_descriptions: List[Tuple[str, str]] = Field(default_factory=list)

    # Environmental attributes
    lighting: str = "normal"  # e.g., dark, dim, normal, bright
    atmosphere: Dict[str, Any] = Field(default_factory=dict)  # e.g., smoke, fog
    sounds: List[str] = Field(default_factory=list)
    smells: List[str] = Field(default_factory=list)

    # Contents of the room
    objects: List[InteractiveObject] = Field(default_factory=list)
    environmental_effects: List[EnvironmentalEffect] = Field(default_factory=list)

    # State flags for tracking changes
    flags: Set[str] = Field(default_factory=set)

    def get_description(self, player_state: Dict) -> str:
        """Generates a dynamic description based on the current state."""
        parts = [self.base_description]

        # Add conditional descriptions
        for condition, desc in self.conditional_descriptions:
            if self._check_condition(condition, player_state):
                parts.append(desc)

        # Add sensory details
        if self.lighting == "dark" and "darkvision" not in player_state.get(
            "abilities", []
        ):
            parts.append("It's too dark to see clearly.")
        elif self.lighting == "dim":
            parts.append("The dim light makes it hard to see details.")

        if self.sounds:
            parts.append(f"You hear {random.choice(self.sounds)}.")

        if self.smells:
            parts.append(f"You smell {random.choice(self.smells)}.")

        # Describe visible objects
        visible_objects = [
            obj for obj in self.objects if self._can_see_object(obj, player_state)
        ]
        if visible_objects:
            obj_descriptions = [
                self._describe_object(obj) for obj in visible_objects[:3]
            ]
            parts.append("You notice " + ", ".join(obj_descriptions) + ".")

        # Describe active environmental effects
        for effect in self.environmental_effects:
            if effect.active and effect.turns_until_trigger <= 1:
                parts.append(f"⚠️ {effect.warning_signs[-1]}")

        return " ".join(parts)

    def _check_condition(self, condition: str, player_state: Dict) -> bool:
        """Evaluates condition strings against room and player state."""
        if condition in self.flags:
            return True
        if condition.startswith("has_item:"):
            item = condition.split(":")[1]
            return item in player_state.get("inventory", [])
        if condition.startswith("hp"):
            import re

            match = re.match(r"hp([<>=])(\d+)", condition)
            if match:
                op, value = match.groups()
                hp = player_state.get("hp", 0)
                return eval(f"{hp}{op}{value}")
        return False

    def _can_see_object(self, obj: InteractiveObject, player_state: Dict) -> bool:
        """Determines if an object is visible to the player."""
        if obj.properties.get("hidden", False):
            return "true_sight" in player_state.get("abilities", [])
        if self.lighting == "dark":
            return "darkvision" in player_state.get("abilities", [])
        return True

    def _describe_object(self, obj: InteractiveObject) -> str:
        """Gets the appropriate description for an object."""
        return obj.description.get(obj.current_state, f"a {obj.name}")


# ============================================
# TACTICAL POSITIONING
# ============================================


class TerrainType(Enum):
    """Defines terrain types that affect movement and combat."""

    NORMAL = "normal"
    DIFFICULT = "difficult"  # Half movement
    HAZARDOUS = "hazardous"  # Damage on enter
    IMPASSABLE = "impassable"
    WATER = "water"
    ICE = "ice"  # Dex save or fall prone
    #! More thematic exploration terrains, could be refactored to their own class.
    GRASSLAND = "grassland"
    FOREST = "forest"
    HILLS = "hills"
    MOUNTAIN = "mountain"
    SWAMP = "swamp"
    DESERT = "desert"
    UNDERGROUND = "underground"
    URBAN = "urban"


class TacticalRoom(DynamicRoom):
    """
    Extends DynamicRoom with tactical positioning for combat encounters.
    """

    # Zone-based positioning system
    zones: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    # Format: {zone_name: {"terrain": TerrainType, "cover": "none|half|full", "elevation": 0}}

    # Character positions within zones
    positions: Dict[str, str] = Field(default_factory=dict)  # character_id -> zone_name

    def get_distance(self, char1_id: str, char2_id: str) -> int:
        """Calculates the distance between two characters based on zones."""
        zone1 = self.positions.get(char1_id, "center")
        zone2 = self.positions.get(char2_id, "center")

        # Simple zone distance map for tactical calculations
        distance_map = {
            ("center", "center"): 0,
            ("center", "north"): 15,
            ("center", "south"): 15,
            ("center", "east"): 15,
            ("center", "west"): 15,
            ("north", "south"): 30,
            ("east", "west"): 30,
        }

        key = tuple(sorted([zone1, zone2]))
        return distance_map.get(key, 20)  # Default distance

    def get_cover_bonus(self, defender_id: str, attacker_id: str) -> int:
        """Calculates AC bonus from cover based on zone properties."""
        defender_zone = self.positions.get(defender_id, "center")
        zone_data = self.zones.get(defender_zone, {})

        cover = zone_data.get("cover", "none")
        cover_bonus = {"none": 0, "half": 2, "three_quarters": 5, "full": 999}

        return cover_bonus.get(cover, 0)

    # ============================================


# FUTURE ENHANCEMENT OPTIONS
# ============================================

"""
FUTURE ENHANCEMENTS (Keep these in mind for later):

1. WEATHER SYSTEM
   - Affects visibility, movement, spell effects
   - Random weather changes
   - Environmental storytelling

2. DAY/NIGHT CYCLE
   - Different encounters
   - NPC schedules
   - Stealth advantages/disadvantages

3. DESTRUCTIBLE ENVIRONMENT
   - Walls can be broken
   - Fire spreads
   - Flooding

4. SMART NPCs
   - NPCs remember previous encounters
   - Faction reputation
   - Dynamic dialogue based on room state

5. PROCEDURAL GENERATION
   - Random room layouts
   - Randomized treasure
   - Scaling difficulty

6. ENVIRONMENTAL STORYTELLING
   - Clues in room descriptions
   - Hidden lore
   - Investigation rewards

7. PERSISTENT WORLD CHANGES
   - Player actions affect future visits
   - NPC reactions to world state
   - Evolving storylines
"""

"""
def create_enhanced_micro_adventure():
    #Your micro-adventure with enhanced environment
    
    # Create the dungeon room with all enhancements
    dungeon_room = TacticalRoom(
        name="Goblin's Lair",
        base_description="A damp stone chamber lit by a flickering torch.",
        conditional_descriptions=[
            ("goblin_dead", "The goblin's body lies crumpled on the floor."),
            ("chest_open", "The chest stands open, revealing its treasures."),
            ("hp<5", "Your vision blurs from your wounds."),
            ("trap_triggered", "Poison darts stick out from the walls!")
        ],
        lighting="dim",
        sounds=["dripping water", "distant scratching", "your own breathing"],
        smells=["mildew", "goblin stench", "old leather"],
        zones={
            "entrance": {"terrain": TerrainType.NORMAL, "cover": "none", "elevation": 0},
            "center": {"terrain": TerrainType.NORMAL, "cover": "none", "elevation": 0},
            "chest_area": {"terrain": TerrainType.DIFFICULT, "cover": "half", "elevation": 0},
            "goblin_corner": {"terrain": TerrainType.NORMAL, "cover": "three_quarters", "elevation": 5}
        },
        positions={"player": "entrance", "goblin_1": "goblin_corner"},
        objects=[
            InteractiveObject(
                name="Iron Chest",
                description={
                    "default": "a sturdy iron chest with an intricate lock",
                    "unlocked": "an unlocked iron chest",
                    "open": "an open chest containing treasures",
                    "trapped": "a chest with a visible poison dart trap!"
                },
                interactions={
                    InteractionType.EXAMINE: {
                        "effects": [{"type": "skill_check", "skill": "investigation", "dc": 12,
                                   "success": {"reveal": "trap", "message": "You spot a poison dart trap!"},
                                   "failure": {"message": "The chest looks valuable."}}]
                    },
                    InteractionType.USE: {
                        "requires": {"item": "golden_key"},
                        "next_state": "unlocked",
                        "message": "The key turns with a satisfying click!"
                    }
                }
            )
        ],
        environmental_effects=[
            EnvironmentalEffect(
                name="Goblin Reinforcements",
                trigger_condition="every_n_turns",
                trigger_frequency=5,
                effect_type="spawn",
                effect_data={"spawn": "goblin_warrior", "location": "entrance"},
                warning_signs=[
                    "You hear footsteps echoing from the entrance...",
                    "The footsteps grow louder!",
                    "Something is coming!"
                ],
                active=True,
                turns_until_trigger=5
            )
        ]
    )
    
    return dungeon_room
"""
