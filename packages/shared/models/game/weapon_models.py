from typing import Any, Dict, List, Optional

from sqlmodel import Field, Relationship, SQLModel


class DamageType(SQLModel, table=True):
    """SQLModel for D&D damage types"""

    __tablename__ = "damage_types"
    index: str = Field(
        primary_key=True, description="Unique identifier for the damage type"
    )
    name: str = Field(description="Display name of the damage type")
    desc: List[str] = Field(
        description="List of description paragraphs explaining the damage type"
    )
    url: str = Field(description="API endpoint URL for this damage type")


class WeaponProperty(SQLModel, table=True):
    """SQLModel for D&D weapon properties"""

    __tablename__ = "weapon_properties"
    index: str = Field(
        primary_key=True, description="Unique identifier for the weapon property"
    )
    name: str = Field(description="Display name of the weapon property")
    desc: List[str] = Field(
        description="List of description paragraphs explaining the property"
    )
    url: str = Field(description="API endpoint URL for this weapon property")


class EquipmentCategory(SQLModel, table=True):
    """SQLModel for D&D equipment categories"""

    __tablename__ = "equipment_categories"
    index: str = Field(
        primary_key=True, description="Unique identifier for the equipment category"
    )
    name: str = Field(description="Display name of the equipment category")
    equipment: List["Equipment"] = Relationship(back_populates="equipment_category")


class Equipment(SQLModel, table=True):
    """SQLModel for D&D equipment items"""

    index: str = Field(
        primary_key=True, description="Unique identifier for the equipment"
    )

    # Basic info
    name: str = Field(description="Display name of the equipment")
    url: str = Field(description="API endpoint URL for this equipment")

    # Foreign key to equipment category
    equipment_category_index: str = Field(
        foreign_key="equipmentcategory.index",
        description="Reference to equipment category",
    )
    equipment_category: EquipmentCategory = Relationship(back_populates="equipment")

    # Weapon-specific fields (Optional since not all equipment are weapons)
    weapon_category: Optional[str] = Field(
        default=None, description="Weapon category (Simple, Martial)"
    )
    weapon_range: Optional[str] = Field(
        default=None, description="Weapon range (Melee, Ranged)"
    )
    category_range: Optional[str] = Field(
        default=None, description="Combined category and range"
    )

    # Cost information stored as JSON
    cost: Optional[Dict[str, Any]] = Field(
        default=None, description="Cost with quantity and unit"
    )

    # Damage information stored as JSON
    damage: Optional[Dict[str, Any]] = Field(
        default=None, description="Damage dice and type information"
    )
    damage_type_index: Optional[str] = Field(
        default=None, foreign_key="damagetype.index"
    )

    # Range information stored as JSON
    range_normal: Optional[int] = Field(default=None)
    range_long: Optional[int] = Field(default=None)
    throw_range_normal: Optional[int] = Field(
        default=None, description="Normal throwing range"
    )
    throw_range_long: Optional[int] = Field(
        default=None, description="Long throwing range "
    )

    # Physical properties
    weight: Optional[float] = Field(default=None, description="Weight of the equipment")


class EquipmentWeaponProperty(SQLModel, table=True):
    """Junction table for equipment-property many-to-many relationship"""

    equipment_index: str = Field(
        foreign_key="equipmentwithforeignkeys.index", primary_key=True
    )
    weapon_property_index: str = Field(
        foreign_key="weaponproperty.index", primary_key=True
    )
