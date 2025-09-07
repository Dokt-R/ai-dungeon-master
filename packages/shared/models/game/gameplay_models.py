from typing import List

from sqlmodel import Field, Relationship, SQLModel

from packages.shared.models.game.base_models import (
    BaseGameElement,
    BaseGameElementWithDesc,
)


class Ability(BaseGameElementWithDesc, table=True):
    """SQLModel for D&D ability scores (STR, DEX, CON, INT, WIS, CHA)"""
    __tablename__ = "abilities"
    full_name: str = Field(description="Full name like 'Strength', 'Dexterity'")
    skills: List["Skill"] = Relationship(back_populates="ability_score")


class Skill(BaseGameElementWithDesc, table=True):
    """SQLModel for D&D skills"""
    __tablename__ = "skills"
    abilities_index: str = Field(foreign_key="abilities.index", description="Which ability score this skill uses")
    ability: Ability = Relationship(back_populates="skills")


# Junction table for ability scores to skills (alternative to direct relationship)
class AbilitySkill(SQLModel, table=True):
    """Junction table for ability score to skill relationships"""
    abilities_index: str = Field(foreign_key="abilities.index", primary_key=True)
    skill_index: str = Field(foreign_key="skills.index", primary_key=True)

class Condition(BaseGameElementWithDesc, table=True):
    """SQLModel for D&D conditions"""
    __tablename__ = "conditions"
    
class Alignment(BaseGameElement, table=True):
    """SQLModel for D&D alignments"""
    abbreviation: str = Field(description="Short abbreviation like 'LG', 'CE'")
    desc: str = Field(description="Description explaining the alignment")
    url: str = Field(description="API endpoint URL for this alignment")