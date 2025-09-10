from typing import Any, Dict, List, Optional

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped
from sqlmodel import Column, Field, Relationship, SQLModel

from packages.shared.models.game.base_models import BaseGameplayModel
from packages.shared.models.game.gameplay_links import (
    AbilitySkillLink,
    ClassProficiencyLink,
    ClassSavingThrowLink,
    LanguageRaceLink,
    LevelFeatureLink,
    MonsterConditionImmunityLink,
    ProficiencyTraitLink,
    RaceTraitLink,
    SpellClassLink,
    SpellSubclassLink,
    SubraceTraitLink,
)


class Ability(BaseGameplayModel, table=True):
    """SQLModel for D&D ability scores (STR, DEX, CON, INT, WIS, CHA)"""
    __tablename__ = "abilities"
    full_name: str = Field(description="Full name like 'Strength', 'Dexterity'")
    skills: Mapped[List['Skill']] = Relationship(back_populates="ability", link_model=AbilitySkillLink)
    desc: Optional[str] = Field(
        default=None,
        description="List of description paragraphs explaining",
        sa_column=Column(JSON),
    )



class Skill(BaseGameplayModel, table=True):
    """SQLModel for D&D skills"""
    __tablename__ = "skills"
    abilities_index: str = Field(foreign_key="abilities.index", description="Which ability score this skill uses")
    ability: Mapped['Ability'] = Relationship(back_populates="skills", link_model=AbilitySkillLink)
    desc: Optional[str] = Field(
        default=None,
        description="List of description paragraphs explaining",
        sa_column=Column(JSON),
    )


class Condition(BaseGameplayModel, table=True):
    """SQLModel for D&D conditions"""
    __tablename__ = "conditions"
    monsters: Mapped[List["Monster"]] = Relationship(back_populates="condition_immunities", link_model=MonsterConditionImmunityLink)
    desc: Optional[str] = Field(
        default=None,
        description="List of description paragraphs explaining",
        sa_column=Column(JSON),
    )

    
class Alignment(BaseGameplayModel, table=True):
    """SQLModel for D&D alignments"""
    abbreviation: str = Field(description="Short abbreviation like 'LG', 'CE'")
    desc: str = Field(description="Description explaining the alignment")


class MagicSchool(BaseGameplayModel, table=True):
    """SQLModel for D&D magic schools"""
    __tablename__ = "magicschools"
    desc: str = Field(description="Description of the magic school")


class Language(BaseGameplayModel, table=True):
    """SQLModel for D&D languages"""
    __tablename__ = "languages"
    type: str = Field(description="Type of language (e.g., 'Standard', 'Exotic')")
    typical_speakers: List[str] = Field(description="List of typical speakers of the language",
        sa_column=Column(JSON),
    )
    script: Optional[str] = Field(default=None, description="Script used for the language")
    races: Mapped[List["Race"]] = Relationship(back_populates="languages", link_model=LanguageRaceLink)
    desc: Optional[str] = Field(
        default=None,
        description="List of description paragraphs explaining",
        sa_column=Column(JSON),
    )


class Trait(BaseGameplayModel, table=True):
    """SQLModel for D&D traits"""
    __tablename__ = "traits"

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
    desc: Optional[str] = Field(
        default=None,
        description="List of description paragraphs explaining",
        sa_column=Column(JSON),
    )


class Proficiency(BaseGameplayModel, table=True):
    """SQLModel for D&D proficiencies"""
    __tablename__= "proficiencies"
    type: str = Field(description="Type of proficiency (e.g., 'Armor', 'Weapons', 'Skills')")
    # races: Mapped[List["Race"] = Relationship(back_populates="proficiencies") # To be implemented later
    # reference: Optional[str] = Field(default=None, description="Reference to the item/category this proficiency applies to") # To be implemented later
    classes: Mapped[List["Class"]] = Relationship(back_populates="proficiencies", link_model=ClassProficiencyLink)
    traits: Mapped[List["Trait"]] = Relationship(back_populates="proficiencies", link_model=ProficiencyTraitLink)


class Race(BaseGameplayModel, table=True):
    """SQLModel for D&D races"""
    __tablename__ = "races"
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
    # Relationships
    languages: Mapped[List["Language"]] = Relationship(back_populates="races", link_model=LanguageRaceLink)
    subraces: List["Subrace"] = Relationship(back_populates="race")
    traits: Mapped[List["Trait"]] = Relationship(back_populates="races", link_model=RaceTraitLink)


class Subrace(BaseGameplayModel, table=True):
    """SQLModel for D&D subraces"""
    __tablename__ = "subraces"
    race_index: str = Field(foreign_key="races.index", description="Parent race")
    desc: str = Field(description="Description")
    ability_bonuses: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON), description="Ability score bonuses")

    # Relationships
    race: Optional["Race"] = Relationship(back_populates="subraces")
    traits: Mapped[List["Trait"]] = Relationship(back_populates="subraces", link_model=SubraceTraitLink)


class Background(BaseGameplayModel, table=True):
    """SQLModel for D&D backgrounds"""
    __tablename__ = "backgrounds"
    starting_proficiencies: List[Dict] = Field(description="List of starting proficiencies",
        sa_column=Column(JSON),
    )
    language_options: Dict = Field(description="Options for starting languages",
        sa_column=Column(JSON),
    )
    starting_equipment: List[Dict] = Field(description="List of starting equipment",
        sa_column=Column(JSON),
    )
    feature: Dict = Field(description="Background feature",
        sa_column=Column(JSON),
    )


class Class(BaseGameplayModel, table=True):
    """SQLModel for D&D classes"""
    __tablename__ = "classes"
    hit_die: int = Field(description="Hit die for the class")
    proficiency_choices: List[Dict] = Field(description="Choices for starting proficiencies",
        sa_column=Column(JSON),
    )
    starting_equipment: List[Dict] = Field(description="List of starting equipment options",
        sa_column=Column(JSON),
    )
    class_levels: str = Field(description="API endpoint for class levels")

    # Relationships
    proficiencies: Mapped[List["Proficiency"]] = Relationship(back_populates="classes", link_model=ClassProficiencyLink)
    saving_throws: Mapped[List["Ability"]] = Relationship(link_model=ClassSavingThrowLink)
    subclasses: List["Subclass"] = Relationship(back_populates="parent_class")
    features: List["Feature"] = Relationship(back_populates="dnd_class")
    levels: List["Level"] = Relationship(back_populates="dnd_class")
    characters: Mapped[List["core_db_models.Character"]] = Relationship(back_populates="dnd_class")


class Subclass(BaseGameplayModel, table=True):
    """SQLModel for D&D subclasses"""
    __tablename__ = "subclasses"
    class_index: str = Field(foreign_key="classes.index", description="Parent class")
    subclass_flavor: str = Field(description="Flavor text for the subclass")
    desc: List[str] = Field(description="Description of the subclass",
        sa_column=Column(JSON),
    )
    subclass_levels: str = Field(description="API endpoint for subclass levels")

    # Relationships
    parent_class: Optional["Class"] = Relationship(back_populates="subclasses")
    features: List["Feature"] = Relationship(back_populates="subclass")
    levels: List["Level"] = Relationship(back_populates="subclass")


class Spell(BaseGameplayModel, table=True):
    """SQLModel for D&D spells"""
    __tablename__ = "spells"
    desc: List[str] = Field(sa_column=Column(JSON))
    higher_level: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    range: str
    components: List[str] = Field(sa_column=Column(JSON))
    material: Optional[str] = Field(default=None)
    ritual: bool
    duration: str
    concentration: bool
    casting_time: str
    level: int
    attack_type: Optional[str] = Field(default=None)
    school_index: str = Field(foreign_key="magicschools.index")

    # JSON blobs for nested objects
    damage: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    dc: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    area_of_effect: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    heal_at_slot_level: Optional[Dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    school: "MagicSchool" = Relationship()
    classes: Mapped[List["Class"]] = Relationship(link_model=SpellClassLink)
    subclasses: Mapped[List["Subclass"]] = Relationship(link_model=SpellSubclassLink)


class Feat(BaseGameplayModel, table=True):
    """SQLModel for D&D feats"""
    __tablename__ = "feats"
    prerequisites: List[Dict] = Field(sa_column=Column(JSON))
    desc: List[str] = Field(sa_column=Column(JSON))


class Feature(BaseGameplayModel, table=True):
    """SQLModel for D&D features"""
    __tablename__ = "features"
    level: int
    desc: List[str] = Field(sa_column=Column(JSON))
    class_index: str = Field(foreign_key="classes.index")
    subclass_index: Optional[str] = Field(default=None, foreign_key="subclasses.index")
    # The feature_specific field can hold complex JSON data for choices
    feature_specific: Optional[Dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    dnd_class: "Class" = Relationship(back_populates="features")
    subclass: Optional["Subclass"] = Relationship(back_populates="features")
    levels: Mapped[List["Level"]] = Relationship(back_populates="features", link_model=LevelFeatureLink)


class Level(SQLModel, table=True):
    """SQLModel for D&D class/subclass level progression"""
    __tablename__ = "levels"
    index: str = Field(primary_key=True)
    level: int
    ability_score_bonuses: Optional[int] = Field(default=None, nullable=True)
    prof_bonus: Optional[int] = Field(default=None, nullable=True)
    class_index: str = Field(foreign_key="classes.index")
    subclass_index: Optional[str] = Field(default=None, foreign_key="subclasses.index", nullable=True)
    url: str

    # JSON blobs for complex data
    class_specific: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    spellcasting: Optional[Dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    dnd_class: "Class" = Relationship(back_populates="levels")
    subclass: Optional["Subclass"] = Relationship(back_populates="levels")
    features: Mapped[List["Feature"]] = Relationship(back_populates="levels", link_model=LevelFeatureLink)


class Monster(BaseGameplayModel, table=True):
    """SQLModel for D&D monsters"""
    __tablename__ = "monsters"
    desc: Optional[str] = None
    size: str
    type: str
    subtype: Optional[str] = None
    alignment: str
    hit_points: int
    hit_dice: str
    hit_points_roll: str
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    challenge_rating: float
    proficiency_bonus: int
    xp: int
    languages: str
    image: Optional[str] = None

    # JSON fields for complex data
    armor_class: List[Dict] = Field(sa_column=Column(JSON))
    speed: Dict[str, Any] = Field(sa_column=Column(JSON))
    senses: Dict[str, Any] = Field(sa_column=Column(JSON))
    proficiencies: List[Dict] = Field(sa_column=Column(JSON))
    damage_vulnerabilities: List[str] = Field(sa_column=Column(JSON))
    damage_resistances: List[str] = Field(sa_column=Column(JSON))
    damage_immunities: List[str] = Field(sa_column=Column(JSON))
    special_abilities: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))
    actions: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))
    legendary_actions: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))
    forms: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    condition_immunities: Mapped[List["Condition"]] = Relationship(back_populates="monsters", link_model=MonsterConditionImmunityLink)
