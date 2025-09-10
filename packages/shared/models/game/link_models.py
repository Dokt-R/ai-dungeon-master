from sqlmodel import Field, SQLModel


class CharacterProficiencyLink(SQLModel, table=True):
    """Junction table for character to proficiency many-to-many relationship"""
    __tablename__ = "character_proficiency_link"
    character_id: int = Field(foreign_key="characters.character_id", primary_key=True)
    proficiency_index: str = Field(foreign_key="proficiencies.index", primary_key=True)