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
