"""
Link tables for many-to-many relationships in the gameplay_models.py file
"""

"""
Link tables for many-to-many relationships in the gameplay_models.py file
"""

from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from packages.shared.models.core_db_models import Character
    from packages.shared.models.game.gameplay_models import Proficiency


class RaceTraitLink(SQLModel, table=True):
    """Junction table for trait to race many-to-many relationship"""

    __tablename__ = "race_trait_link"
    trait_index: str = Field(foreign_key="traits.index", primary_key=True)
    race_index: str = Field(foreign_key="races.index", primary_key=True)


class SubraceTraitLink(SQLModel, table=True):
    """Junction table for trait to subrace many-to-many relationship"""

    __tablename__ = "subrace_trait_link"
    trait_index: str = Field(foreign_key="traits.index", primary_key=True)
    subrace_index: str = Field(foreign_key="subraces.index", primary_key=True)


class ProficiencyTraitLink(SQLModel, table=True):
    """Junction table for trait to proficiency many-to-many relationship"""

    __tablename__ = "proficiency_trait_link"
    trait_index: str = Field(foreign_key="traits.index", primary_key=True)
    proficiency_index: str = Field(foreign_key="proficiencies.index", primary_key=True)


class AbilitySkillLink(SQLModel, table=True):
    """Junction table for ability score to skill relationships"""

    __tablename__ = "ability_skill_link"
    abilities_index: str = Field(foreign_key="abilities.index", primary_key=True)
    skill_index: str = Field(foreign_key="skills.index", primary_key=True)


class LanguageRaceLink(SQLModel, table=True):
    """Junction table for race to language many-to-many relationship"""

    __tablename__ = "language_race_link"
    race_index: str = Field(foreign_key="races.index", primary_key=True)
    language_index: str = Field(foreign_key="languages.index", primary_key=True)


class ClassProficiencyLink(SQLModel, table=True):
    """Junction table for class to proficiency many-to-many relationship"""

    __tablename__ = "class_proficiency_link"
    class_index: str = Field(foreign_key="classes.index", primary_key=True)
    proficiency_index: str = Field(foreign_key="proficiencies.index", primary_key=True)


class ClassSavingThrowLink(SQLModel, table=True):
    """Junction table for class to saving throw many-to-many relationship"""

    __tablename__ = "class_saving_throw_link"
    class_index: str = Field(foreign_key="classes.index", primary_key=True)
    ability_index: str = Field(foreign_key="abilities.index", primary_key=True)


class SpellClassLink(SQLModel, table=True):
    """Junction table for spell to class many-to-many relationship"""

    __tablename__ = "spell_class_link"
    spell_index: str = Field(foreign_key="spells.index", primary_key=True)
    class_index: str = Field(foreign_key="classes.index", primary_key=True)


class SpellSubclassLink(SQLModel, table=True):
    """Junction table for spell to subclass many-to-many relationship"""

    __tablename__ = "spell_subclass_link"
    spell_index: str = Field(foreign_key="spells.index", primary_key=True)
    subclass_index: str = Field(foreign_key="subclasses.index", primary_key=True)


class LevelFeatureLink(SQLModel, table=True):
    """Junction table for level to feature many-to-many relationship"""

    __tablename__ = "level_feature_link"
    level_index: str = Field(foreign_key="levels.index", primary_key=True)
    feature_index: str = Field(foreign_key="features.index", primary_key=True)


class MonsterConditionImmunityLink(SQLModel, table=True):
    """Junction table for monster to condition immunity many-to-many relationship"""

    __tablename__ = "monster_condition_immunity_link"
    monster_index: str = Field(foreign_key="monsters.index", primary_key=True)
    condition_index: str = Field(foreign_key="conditions.index", primary_key=True)


class ProficiencyLevel(str, Enum):
    """Enum for proficiency levels."""

    NONE = "none"
    HALF = "half"
    PROFICIENT = "proficient"
    EXPERTISE = "expertise"


class CharacterProficiencyLink(SQLModel, table=True):
    """Link table between Character and Proficiency, storing the level of proficiency."""

    __tablename__ = "character_proficiencies"
    character_id: int = Field(
        primary_key=True, foreign_key="characters.character_id"
    )
    proficiency_index: str = Field(
        primary_key=True, foreign_key="proficiencies.index"
    )
    level: ProficiencyLevel = Field(default=ProficiencyLevel.PROFICIENT)

    character: "Character" = Relationship(back_populates="proficiency_links")
    proficiency: "Proficiency" = Relationship(back_populates="character_links")
