from typing import Dict, List, Optional

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped
from sqlmodel import Column, Field, Relationship, SQLModel

# Links

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
    skills: Mapped[List['Skill']] = Relationship(back_populates="ability", link_model=AbilitySkillLink)


class Skill(SQLModel, table=True):
    """SQLModel for D&D skills"""
    __tablename__ = "skills"
    index: str = Field(primary_key=True, description="Unique identifier like 'athletics', 'stealth'")
    name: str = Field(description="Skill name like 'Athletics', 'Stealth'")
    desc: str = Field(description="List of description paragraphs explaining the skill",
        sa_column=Column(JSON),
    )
    abilities_index: str = Field(foreign_key="abilities.index", description="Which ability score this skill uses")
    ability: Mapped['Ability'] = Relationship(back_populates="skills", link_model=AbilitySkillLink)
    url: str = Field(description="API endpoint URL for this skill")


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
    races: Mapped[List["Race"]] = Relationship(back_populates="languages", link_model=LanguageRaceLink)


class Trait(SQLModel, table=True):
    """SQLModel for D&D traits"""
    __tablename__ = "traits"
    index: str = Field(primary_key=True, description="Unique identifier like 'darkvision', 'dwarven-resilience'")
    name: str = Field(description="Trait name like 'Darkvision', 'Dwarven Resilience'")
    desc: List[str] = Field(description="List of description paragraphs explaining the trait",
        sa_column=Column(JSON),
    )
    url: str = Field(description="API endpoint URL for this trait")

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

    # Relationships
    proficiencies: Mapped[List["Proficiency"]] = Relationship(back_populates="traits", link_model=ProficiencyTraitLink)
    races: Mapped[List["Race"]] = Relationship(back_populates="traits", link_model=RaceTraitLink)
    subraces: Mapped[List["Subrace"]] = Relationship(back_populates="traits", link_model=SubraceTraitLink)


class Proficiency(SQLModel, table=True):
    """SQLModel for D&D proficiencies"""
    __tablename__= "proficiencies"
    index: str = Field(primary_key=True, description="Unique identifier like 'light-armor', 'simple-weapons'")
    type: str = Field(description="Type of proficiency (e.g., 'Armor', 'Weapons', 'Skills')")
    name: str = Field(description="Proficiency name like 'Light Armor', 'Simple Weapons'")
    url: str = Field(description="API endpoint URL for this proficiency")
    # classes: List["Class"] = Relationship(back_populates="proficiencies") # To be implemented later
    # races: Mapped[List["Race"] = Relationship(back_populates="proficiencies") # To be implemented later
    # reference: Optional[str] = Field(default=None, description="Reference to the item/category this proficiency applies to") # To be implemented later

    traits: Mapped[List["Trait"]] = Relationship(back_populates="proficiencies", link_model=ProficiencyTraitLink)


class Race(SQLModel, table=True):
    """SQLModel for D&D races"""
    __tablename__ = "races"
    index: str = Field(primary_key=True, description="Unique identifier like 'dwarf', 'elf'")
    name: str = Field(description="Race name like 'Dwarf', 'Elf'")
    speed: int = Field(description="Base walking speed")
    alignment: str = Field(description="Typical alignment description")
    age: str = Field(description="Age description")
    size: str = Field(description="Size category like 'Medium'")
    size_description: str = Field(description="Detailed size description")
    language_desc: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    language_options: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    desc: Optional[List[str]] = Field(description="Description paragraphs",
        sa_column=Column(JSON),
    )
    ability_bonuses: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON), description="Ability score bonuses")
    # traits: List[str] = Field(description="Description paragraphs",
    #     sa_column=Column(JSON),
    # )
    url: str = Field(description="API endpoint URL for this race")
    # Relationships
    languages: Mapped[List["Language"]] = Relationship(back_populates="races", link_model=LanguageRaceLink)
    subraces: List["Subrace"] = Relationship(back_populates="race")
    traits: Mapped[List["Trait"]] = Relationship(back_populates="races", link_model=RaceTraitLink)


class Subrace(SQLModel, table=True):
    """SQLModel for D&D subraces"""
    __tablename__ = "subraces"
    index: str = Field(primary_key=True, description="Unique identifier like 'hill-dwarf'")
    race_index: str = Field(foreign_key="races.index", description="Parent race")
    name: str = Field(description="Subrace name like 'Hill Dwarf'")
    desc: str = Field(description="Description")
    ability_bonuses: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON), description="Ability score bonuses")
    url: str = Field(description="API endpoint URL for this subrace")
    # Relationships
    race: Optional["Race"] = Relationship(back_populates="subraces")
    traits: Mapped[List["Trait"]] = Relationship(back_populates="subraces", link_model=SubraceTraitLink)