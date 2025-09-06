from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


# Enums for better type safety
class OptionType(str, Enum):
    REFERENCE = "reference"
    COUNTED_REFERENCE = "counted_reference"
    CHOICE = "choice"


class OptionSetType(str, Enum):
    OPTIONS_ARRAY = "options_array"
    EQUIPMENT_CATEGORY = "equipment_category"


# Base reference model for items that will have their own tables
class ItemReference(SQLModel):
    index: str
    name: str
    url: str


# Equipment placeholder - will be its own table
class Equipment(SQLModel, table=True):
    index: str = Field(primary_key=True)
    name: str
    url: str
    # Add other equipment fields as needed
    equipment_category: Optional[str] = None


# Proficiency placeholder - will be its own table
class Proficiency(SQLModel, table=True):
    index: str = Field(primary_key=True)
    name: str
    url: str
    type: Optional[str] = None  # skill, saving-throw, armor, weapon, etc.


# Ability Score placeholder - will be its own table
class AbilityScore(SQLModel, table=True):
    index: str = Field(primary_key=True)
    name: str
    url: str
    full_name: Optional[str] = None


# Equipment Category placeholder - will be its own table
class EquipmentCategory(SQLModel, table=True):
    index: str = Field(primary_key=True)
    name: str
    url: str


# Junction table for class proficiencies
class ClassProficiency(SQLModel, table=True):
    class_index: str = Field(foreign_key="dndclass.index", primary_key=True)
    proficiency_index: str = Field(foreign_key="proficiency.index", primary_key=True)


# Junction table for class saving throws
class ClassSavingThrow(SQLModel, table=True):
    class_index: str = Field(foreign_key="dndclass.index", primary_key=True)
    ability_score_index: str = Field(foreign_key="abilityscore.index", primary_key=True)


# Starting equipment for classes
class ClassStartingEquipment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    class_index: str = Field(foreign_key="dndclass.index")
    equipment_index: str = Field(foreign_key="equipment.index")
    quantity: int


# Models for equipment choice options
class EquipmentOption(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    choice_id: int = Field(foreign_key="equipmentchoice.id")
    option_type: OptionType
    count: Optional[int] = None
    equipment_index: Optional[str] = Field(default=None, foreign_key="equipment.index")
    # For nested choices
    nested_choice_desc: Optional[str] = None
    nested_choice_from_category: Optional[str] = Field(
        default=None, foreign_key="equipmentcategory.index"
    )


class EquipmentChoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    class_index: str = Field(foreign_key="dndclass.index")
    description: str
    choose_count: int

    # Relationship to options
    options: List[EquipmentOption] = Relationship(back_populates="choice")


# Update EquipmentOption to include the relationship
EquipmentOption.choice = Relationship(back_populates="options")


# Models for proficiency choice options
class ProficiencyOption(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    choice_id: int = Field(foreign_key="proficiencychoice.id")
    proficiency_index: str = Field(foreign_key="proficiency.index")


class ProficiencyChoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    class_index: str = Field(foreign_key="dndclass.index")
    description: str
    choose_count: int

    # Relationship to options
    options: List[ProficiencyOption] = Relationship(back_populates="choice")


# Update ProficiencyOption to include the relationship
ProficiencyOption.choice = Relationship(back_populates="options")


# Multiclassing prerequisites
class MulticlassPrerequisite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    class_index: str = Field(foreign_key="dndclass.index")
    ability_score_index: str = Field(foreign_key="abilityscore.index")
    minimum_score: int


# Junction table for multiclass proficiencies
class MulticlassProficiency(SQLModel, table=True):
    class_index: str = Field(foreign_key="dndclass.index", primary_key=True)
    proficiency_index: str = Field(foreign_key="proficiency.index", primary_key=True)


# Subclass placeholder - will be its own table
class Subclass(SQLModel, table=True):
    index: str = Field(primary_key=True)
    name: str
    url: str
    class_index: str = Field(foreign_key="dndclass.index")


# Main DnD Class model
class DnDClass(SQLModel, table=True):
    __tablename__ = "dndclass"

    index: str = Field(primary_key=True)
    name: str
    hit_die: int
    class_levels_url: str = Field(alias="class_levels")
    url: str

    # Relationships
    proficiencies: List[Proficiency] = Relationship(
        back_populates="classes", link_model=ClassProficiency
    )
    saving_throws: List[AbilityScore] = Relationship(
        back_populates="classes", link_model=ClassSavingThrow
    )
    starting_equipment: List[ClassStartingEquipment] = Relationship(
        back_populates="dnd_class"
    )
    equipment_choices: List[EquipmentChoice] = Relationship(back_populates="dnd_class")
    proficiency_choices: List[ProficiencyChoice] = Relationship(
        back_populates="dnd_class"
    )
    multiclass_prerequisites: List[MulticlassPrerequisite] = Relationship(
        back_populates="dnd_class"
    )
    multiclass_proficiencies: List[Proficiency] = Relationship(
        back_populates="multiclass_classes", link_model=MulticlassProficiency
    )
    subclasses: List[Subclass] = Relationship(back_populates="parent_class")


# Update related models to include back relationships
Equipment.starting_equipment = Relationship(back_populates="equipment")
ClassStartingEquipment.dnd_class = Relationship(back_populates="starting_equipment")
ClassStartingEquipment.equipment = Relationship(back_populates="starting_equipment")

EquipmentChoice.dnd_class = Relationship(back_populates="equipment_choices")
ProficiencyChoice.dnd_class = Relationship(back_populates="proficiency_choices")

Proficiency.classes = Relationship(
    back_populates="proficiencies", link_model=ClassProficiency
)
Proficiency.multiclass_classes = Relationship(
    back_populates="multiclass_proficiencies", link_model=MulticlassProficiency
)

AbilityScore.classes = Relationship(
    back_populates="saving_throws", link_model=ClassSavingThrow
)

MulticlassPrerequisite.dnd_class = Relationship(
    back_populates="multiclass_prerequisites"
)
MulticlassPrerequisite.ability_score = Relationship()

Subclass.parent_class = Relationship(back_populates="subclasses")


# Example usage and data insertion helper
def create_barbarian_class() -> DnDClass:
    """Helper function to create a Barbarian class instance with the provided data"""
    return DnDClass(
        index="barbarian",
        name="Barbarian",
        hit_die=12,
        class_levels_url="/api/2014/classes/barbarian/levels",
        url="/api/2014/classes/barbarian",
    )
