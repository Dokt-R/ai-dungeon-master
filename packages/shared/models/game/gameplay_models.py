from typing import List, Optional

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