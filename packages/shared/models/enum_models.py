"""
Enum Models
Enums used for as a single source of truth for field validations.
"""

from enum import Enum


class DMVisibility(str, Enum):
    public = "public"
    hidden = "hidden"


class PlayerRollMode(str, Enum):
    physical = "physical"
    digital = "digital"
    auto = "auto"
    hidden = "hidden"


class CharacterSheetMode(str, Enum):
    digital_sheet = "digital_sheet"
    physical_sheet = "physical_sheet"


class AbilityName(str, Enum):
    STRENGTH = "str"
    DEXTERITY = "dex"
    CONSTITUTION = "con"
    INTELLIGENCE = "int"
    WISDOM = "wis"
    CHARISMA = "cha"


class SkillName(str, Enum):
    ACROBATICS = "acrobatics"
    ANIMAL_HANDLING = "animal_handling"
    ARCANA = "arcana"
    ATHLETICS = "athletics"
    DECEPTION = "deception"
    HISTORY = "history"
    INSIGHT = "insight"
    INTIMIDATION = "int_intimidation"  # Renamed to avoid conflict with INT ability
    INVESTIGATION = "investigation"
    MEDICINE = "medicine"
    NATURE = "nature"
    PERCEPTION = "perception"
    PERFORMANCE = "performance"
    PERSUASION = "persuasion"
    RELIGION = "religion"
    SLEIGHT_OF_HAND = "sleight_of_hand"
    STEALTH = "stealth"
    SURVIVAL = "survival"


# Mapping skills to their primary ability scores
SKILL_TO_ABILITY_MAP = {
    SkillName.ACROBATICS: AbilityName.DEXTERITY,
    SkillName.ANIMAL_HANDLING: AbilityName.WISDOM,
    SkillName.ARCANA: AbilityName.INTELLIGENCE,
    SkillName.ATHLETICS: AbilityName.STRENGTH,
    SkillName.DECEPTION: AbilityName.CHARISMA,
    SkillName.HISTORY: AbilityName.INTELLIGENCE,
    SkillName.INSIGHT: AbilityName.WISDOM,
    SkillName.INTIMIDATION: AbilityName.CHARISMA,
    SkillName.INVESTIGATION: AbilityName.INTELLIGENCE,
    SkillName.MEDICINE: AbilityName.WISDOM,
    SkillName.NATURE: AbilityName.INTELLIGENCE,
    SkillName.PERCEPTION: AbilityName.WISDOM,
    SkillName.PERFORMANCE: AbilityName.CHARISMA,
    SkillName.PERSUASION: AbilityName.CHARISMA,
    SkillName.RELIGION: AbilityName.INTELLIGENCE,
    SkillName.SLEIGHT_OF_HAND: AbilityName.DEXTERITY,
    SkillName.STEALTH: AbilityName.DEXTERITY,
    SkillName.SURVIVAL: AbilityName.WISDOM,
}
