from typing import Dict, List, Optional

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped
from sqlmodel import Column, Field, Relationship, SQLModel

# class BaseGameElement(SQLModel):
#     """Base class for most D&D game elements"""
    
#     # Common fields across most models
#     index: str = Field(primary_key=True, description="Unique identifier")
#     name: str = Field(description="Display name")
#     url: str = Field(description="API endpoint URL")
#     desc: Optional[str] = Field(default = None, description="List of description paragraphs explaining the ability score",
#         sa_column=Column(JSON),
#     )

class Ability(SQLModel, table=True):
    """SQLModel for D&D ability scores (STR, DEX, CON, INT, WIS, CHA)"""
    __tablename__ = "abilities"
    index: str = Field(primary_key=True, description="Unique identifier like 'str', 'dex'")
    name: str = Field(description="Short name like 'STR', 'DEX'")
    full_name: str = Field(description="Full name like 'Strength', 'Dexterity'")
    desc: str = Field(description="List of description paragraphs explaining the ability score",
        sa_column=Column(JSON),
    )
    url: str = Field(description="API endpoint URL for this ability score")
    skills: Mapped[List['Skill']] = Relationship(back_populates="ability")


class Skill(SQLModel, table=True):
    """SQLModel for D&D skills"""
    __tablename__ = "skills"
    index: str = Field(primary_key=True, description="Unique identifier like 'athletics', 'stealth'")
    name: str = Field(description="Skill name like 'Athletics', 'Stealth'")
    desc: str = Field(description="List of description paragraphs explaining the skill",
        sa_column=Column(JSON),
    )
    abilities_index: str = Field(foreign_key="abilities.index", description="Which ability score this skill uses")
    ability: Mapped['Ability'] = Relationship(back_populates="skills")
    url: str = Field(description="API endpoint URL for this skill")


# Junction table for ability scores to skills (alternative to direct relationship)
class AbilitySkill(SQLModel, table=True):
    """Junction table for ability score to skill relationships"""
    abilities_index: str = Field(foreign_key="abilities.index", primary_key=True)
    skill_index: str = Field(foreign_key="skills.index", primary_key=True)

class Condition(SQLModel, table=True):
    """SQLModel for D&D conditions"""
    __tablename__ = "conditions"
    index: str = Field(primary_key=True, description="Unique identifier like 'blinded', 'charmed'")
    name: str = Field(description="Condition name like 'Blinded', 'Charmed'")
    desc: str = Field(description="List of description bullet points explaining the condition effects",
        sa_column=Column(JSON),
    )
    url: str = Field(description="API endpoint URL for this condition")

    
class Alignment(SQLModel, table=True):
    """SQLModel for D&D alignments"""
    index: str = Field(primary_key=True, description="Unique identifier like 'lawful-good', 'chaotic-evil'")
    name: str = Field(description="Full name like 'Lawful Good', 'Chaotic Evil'")
    abbreviation: str = Field(description="Short abbreviation like 'LG', 'CE'")
    desc: str = Field(description="Description explaining the alignment")
    url: str = Field(description="API endpoint URL for this alignment")


class MagicSchool(SQLModel, table=True):
    """SQLModel for D&D magic schools"""
    index: str = Field(primary_key=True, description="Unique identifier like 'abjuration', 'conjuration'")
    name: str = Field(description="Magic school name like 'Abjuration', 'Conjuration'")
    desc: str = Field(description="Description of the magic school")
    url: str = Field(description="API endpoint URL for this magic school")


class Language(SQLModel, table=True):
    """SQLModel for D&D languages"""
    __tablename__ = "languages"
    index: str = Field(primary_key=True, description="Unique identifier like 'common', 'elvish'")
    name: str = Field(description="Language name like 'Common', 'Elvish'")
    desc: Optional[str] = Field(default=None, description="Description of the language",
        sa_column=Column(JSON),
    )
    type: str = Field(description="Type of language (e.g., 'Standard', 'Exotic')")
    typical_speakers: List[str] = Field(description="List of typical speakers of the language",
        sa_column=Column(JSON),
    )
    script: Optional[str] = Field(default=None, description="Script used for the language")
    url: str = Field(description="API endpoint URL for this language")


class TraitProficiency(SQLModel, table=True):
    """Junction table for trait to proficiency many-to-many relationship"""
    __tablename__ = "trait_proficiencies"
    trait_index: str = Field(foreign_key="traits.index", primary_key=True)
    proficiency_index: str = Field(foreign_key="proficiencies.index", primary_key=True)


class Trait(SQLModel, table=True):
    """SQLModel for D&D traits"""
    __tablename__ = "traits"
    index: str = Field(primary_key=True, description="Unique identifier like 'darkvision', 'dwarven-resilience'")
    name: str = Field(description="Trait name like 'Darkvision', 'Dwarven Resilience'")
    desc: List[str] = Field(description="List of description paragraphs explaining the trait",
        sa_column=Column(JSON),
    )
    url: str = Field(description="API endpoint URL for this trait")
    # relationships to be implemented later:
    # races: List["Race"] = Relationship(back_populates="traits")
    # subraces: List["Subrace"] = Relationship(back_populates="traits")
    proficiencies: Mapped[List["Proficiency"]] = Relationship(back_populates="traits", link_model=TraitProficiency)

    # Complex JSON fields for various options
    proficiency_choices: Optional[Dict] = Field(default=None, description="Choices for proficiencies granted by the trait",
        sa_column=Column(JSON),
    )
    language_options: Optional[Dict] = Field(default=None, description="Choices for languages granted by the trait",
        sa_column=Column(JSON),
    )
    spell_options: Optional[Dict] = Field(default=None, description="Choices for spells granted by the trait",
        sa_column=Column(JSON),
    )
    subtrait_options: Optional[Dict] = Field(default=None, description="Choices for subtraits related to the trait",
        sa_column=Column(JSON),
    )
    trait_specific: Optional[Dict] = Field(default=None, description="Specific details for the trait",
        sa_column=Column(JSON),
    )


class Proficiency(SQLModel, table=True):
    """SQLModel for D&D proficiencies"""
    __tablename__= "proficiencies"
    index: str = Field(primary_key=True, description="Unique identifier like 'light-armor', 'simple-weapons'")
    type: str = Field(description="Type of proficiency (e.g., 'Armor', 'Weapons', 'Skills')")
    name: str = Field(description="Proficiency name like 'Light Armor', 'Simple Weapons'")
    url: str = Field(description="API endpoint URL for this proficiency")
    # classes: List["Class"] = Relationship(back_populates="proficiencies") # To be implemented later
    # races: List["Race"] = Relationship(back_populates="proficiencies") # To be implemented later
    # reference: Optional[str] = Field(default=None, description="Reference to the item/category this proficiency applies to") # To be implemented later

    traits: Mapped[List["Trait"]] = Relationship(back_populates="proficiencies", link_model=TraitProficiency)