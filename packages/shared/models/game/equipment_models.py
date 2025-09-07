import json
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, Relationship, SQLModel

from packages.shared.models.game.base_models import (
    BaseGameElement,
    BaseGameElementWithDesc,
)


class EquipmentSlot(Enum):
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    BOTH_HANDS = "both_hands"  # Two-handed weapons
    ARMOR = "armor"
    SHIELD = "shield"  # Special case - goes in off_hand but is armor
    HEAD = "head"
    EYES = "eyes"
    NECK = "neck"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    FEET = "feet"
    HANDS = "hands"  # Gloves
    BELT = "belt"
    CLOAK = "cloak"


@dataclass
class SlotConflict:
    """Represents which slots conflict with each other"""

    primary_slot: EquipmentSlot
    conflicts_with: Set[EquipmentSlot]


# Define slot conflicts
SLOT_CONFLICTS = [
    SlotConflict(
        EquipmentSlot.BOTH_HANDS,
        {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.SHIELD},
    ),
    SlotConflict(EquipmentSlot.MAIN_HAND, {EquipmentSlot.BOTH_HANDS}),
    SlotConflict(
        EquipmentSlot.OFF_HAND, {EquipmentSlot.BOTH_HANDS, EquipmentSlot.SHIELD}
    ),
    SlotConflict(
        EquipmentSlot.SHIELD, {EquipmentSlot.BOTH_HANDS, EquipmentSlot.OFF_HAND}
    ),
]


class DamageType(SQLModel, table=True):
    """SQLModel for D&D damage types"""

    __tablename__ = "damage_types"
    index: str = Field(
        primary_key=True, description="Unique identifier for the damage type"
    )
    name: str = Field(description="Display name of the damage type")
    desc: str = Field(
        description="List of description paragraphs explaining the damage type",
        sa_column=Column(JSON),
    )
    url: str = Field(description="API endpoint URL for this damage type")


class WeaponProperty(SQLModel, table=True):
    """SQLModel for D&D weapon properties"""

    __tablename__ = "weapon_properties"
    index: str = Field(
        primary_key=True, description="Unique identifier for the weapon property"
    )
    name: str = Field(description="Display name of the weapon property")
    desc: str = Field(
        description="List of description paragraphs explaining the property",
        sa_column=Column(JSON),
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
        foreign_key="equipment_categories.index",
        description="Reference to equipment category",
    )
    equipment_category: EquipmentCategory = Relationship(back_populates="equipment")

    # Cost information
    cost_quantity: Optional[int] = Field(
        default=None, description="Cost with quantity in coins"
    )
    cost_unit: Optional[str] = Field(
        default=None, description="Cost unit, as in sp, gp."
    )

    # Physical properties
    weight: Optional[float] = Field(default=None, description="Weight of the equipment")

    # Special properties (e.g Lance disadvantage on 5ft)
    special: Optional[str] = Field(
        default=None,
        description="Special conditions to resolve",
        sa_column=Column(JSON),
    )

    desc: Optional[str] = Field(
        default=None,
        description="Special conditions to resolve",
        sa_column=Column(JSON),
    )


class EquipmentWeaponProperty(SQLModel, table=True):
    """Junction table for equipment-property many-to-many relationship"""

    equipment_index: str = Field(foreign_key="equipment.index", primary_key=True)
    weapon_property_index: str = Field(
        foreign_key="weapon_properties.index", primary_key=True
    )


# Specific tables for each type
class Weapon(SQLModel, table=True):
    equipment_index: str = Field(foreign_key="equipment.index", primary_key=True)
    weapon_category: Optional[str] = Field(
        default=None, description="Weapon category (Simple, Martial)"
    )

    category_range: Optional[str] = Field(
        default=None, description="Combined category and range"
    )

    # Damage information stored as JSON
    damage_dice: Optional[str] = Field(
        default=None, description="Damage dice and type information"
    )
    damage_type_index: Optional[str] = Field(
        default=None, foreign_key="damage_types.index"
    )
    versatile_damage_dice: Optional[str] = Field(
        default=None,
        description="Damage dice for versatile when wielded with two hands",
    )
    versatile_damage_type_index: Optional[str] = Field(
        default=None,
        description="Damage type for versatile when wielded with two hands",
    )

    # Range information stored as JSON
    weapon_range: Optional[str] = Field(
        default=None, description="Weapon range (Melee, Ranged)"
    )
    range_normal: Optional[int] = Field(default=None)
    range_long: Optional[int] = Field(default=None)
    throw_range_normal: Optional[int] = Field(
        default=None, description="Normal throwing range"
    )
    throw_range_long: Optional[int] = Field(
        default=None, description="Long throwing range "
    )


class Armor(SQLModel, table=True):
    equipment_index: str = Field(foreign_key="equipment.index", primary_key=True)
    armor_category: (
        str  # Light, Medium, Heavy, Shield #! Need an is_shield() check somewhere
    )
    armor_class_base: int
    dex_bonus: Optional[bool] = True  #! What is dex bonus?
    max_dex_bonus: Optional[int] = None  #! what is max_dex bonus?
    min_strength: Optional[int] = None
    stealth_disadvantage: bool = False


class Gear(SQLModel, table=True):
    equipment_index: str = Field(foreign_key="equipment.index", primary_key=True)

    gear_category: Optional[str] = Field(
        default=None, description="Adventuring gear, Tools, etc."
    )
    quantity: Optional[int] = None


class Tool(SQLModel, table=True):
    """SQLModel for D&D tools - extends Equipment"""

    # Foreign key to Equipment table
    equipment_index: str = Field(foreign_key="equipment.index", primary_key=True)

    # Tool-specific fields
    tool_category: str = Field(
        description="Category like 'Artisan's Tools', 'Gaming Sets', 'Other Tools'"
    )


class EquipmentPackContent(SQLModel, table=True):
    """Junction table for pack contents. What items are included in equipment packs
    #! Needs give_pack_to_character helper function to handle
    # def give_pack_to_character(character_id: str, pack_index: str, session: Session):
    # Get pack contents
    contents = session.exec(
        select(EquipmentPackContent)
        .where(EquipmentPackContent.pack_index == pack_index)
    ).all()

    # Add each item to character's inventory
    for content in contents:
        char_equipment = CharacterEquipment(
            character_id=character_id,
            equipment_index=content.item_index,
            quantity=content.quantity,
            equipped=False
        )
        session.add(char_equipment)

    # Don't give them the pack container itself (or do, if you want)
    """

    pack_index: str = Field(foreign_key="equipment.index", primary_key=True)
    item_index: str = Field(foreign_key="equipment.index", primary_key=True)
    quantity: int = Field(description="How many of this item are in the pack")


class EquipmentSlotRequirement(SQLModel, table=True):
    """Defines what slots an equipment item can be equipped to"""

    equipment_index: str = Field(foreign_key="equipment.index", primary_key=True)
    slot: EquipmentSlot = Field(primary_key=True)
    is_primary: bool = Field(default=True)


class MountAndVehicle(SQLModel, table=True):
    """SQLModel for D&D vehicles - extends Equipment"""

    __tablename__ = "mounts_and_vehicles"
    # Foreign key to Equipment table
    equipment_index: str = Field(foreign_key="equipment.index", primary_key=True)

    # Vehicle-specific fields
    vehicle_category: str = Field(
        description="Category like 'Waterborne Vehicles', 'Tack, Harness, and Drawn Vehicles'"
    )

    # Speed information (optional - not all vehicles have speed listed)
    speed_quantity: Optional[int] = Field(default=None, description="Speed value")
    speed_unit: Optional[str] = Field(
        default=None, description="Speed unit (mph, ft/round, etc.)"
    )

    # Optional vehicle stats that might appear in expanded rules
    capacity: Optional[int] = Field(
        default=None, description="Cargo capacity in pounds"
    )
    crew_min: Optional[int] = Field(default=None, description="Minimum crew required")
    crew_max: Optional[int] = Field(default=None, description="Maximum crew capacity")
    passengers: Optional[int] = Field(default=None, description="Passenger capacity")
    ac: Optional[int] = Field(default=None, description="Armor Class")
    hp: Optional[int] = Field(default=None, description="Hit Points")
    damage_threshold: Optional[int] = Field(
        default=None, description="Damage threshold"
    )


class CharacterEquipment(SQLModel, table=True):
    character_id: str = Field(foreign_key="characters.character_id", primary_key=True)
    equipment_index: str = Field(foreign_key="equipment.index", primary_key=True)
    quantity: int = 1
    equipped: bool = False
    slot: Optional[str] = None  # "main_hand", "armor", "ring1", etc.


# class EquipmentValidator:
#     """Handles equipment slot validation using existing data"""

#     @staticmethod
#     def get_valid_slots(equipment_index: str, session: Session) -> List[EquipmentSlot]:
#         requirements = session.exec(
#             select(EquipmentSlotRequirement)
#             .where(EquipmentSlotRequirement.equipment_index == equipment_index)
#         ).all()
#         return [req.slot for req in requirements]

#     @staticmethod
#     def has_weapon_property(equipment_index: str, property_name: str, session: Session) -> bool:
#         """Check if weapon has a specific property using existing junction table"""
#         from your_existing_models import EquipmentWeaponProperty, WeaponProperty

#         property_exists = session.exec(
#             select(EquipmentWeaponProperty)
#             .join(WeaponProperty)
#             .where(EquipmentWeaponProperty.equipment_index == equipment_index)
#             .where(WeaponProperty.index == property_name)
#         ).first()

#         return property_exists is not None

#     @staticmethod
#     def is_two_handed(equipment_index: str, session: Session) -> bool:
#         """Check if weapon has two-handed property"""
#         return EquipmentValidator.has_weapon_property(equipment_index, "two-handed", session)

#     @staticmethod
#     def is_versatile(equipment_index: str, session: Session) -> bool:
#         """Check if weapon has versatile property"""
#         return EquipmentValidator.has_weapon_property(equipment_index, "versatile", session)

#     @staticmethod
#     def is_shield(equipment_index: str, session: Session) -> bool:
#         """Check if item is a shield using equipment category"""
#         from your_existing_models import Equipment, EquipmentCategory

#         equipment = session.exec(
#             select(Equipment)
#             .join(EquipmentCategory)
#             .where(Equipment.index == equipment_index)
#             .where(EquipmentCategory.name == "Shield")  # Or however shields are categorized
#         ).first()

#         return equipment is not None

#     @staticmethod
#     def get_conflicting_slots(equipment_index: str, target_slot: EquipmentSlot, session: Session) -> Set[EquipmentSlot]:
#         """Get slots that conflict based on equipment properties"""
#         conflicts = set()

#         # Two-handed weapons conflict with off-hand and shield
#         if EquipmentValidator.is_two_handed(equipment_index, session) or target_slot == EquipmentSlot.BOTH_HANDS:
#             conflicts.update({EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.SHIELD})

#         # Shield conflicts with two-handed and off-hand weapons
#         if EquipmentValidator.is_shield(equipment_index, session) or target_slot == EquipmentSlot.SHIELD:
#             conflicts.update({EquipmentSlot.BOTH_HANDS, EquipmentSlot.OFF_HAND})

#         # Main hand conflicts with two-handed
#         if target_slot == EquipmentSlot.MAIN_HAND:
#             conflicts.add(EquipmentSlot.BOTH_HANDS)

#         # Off-hand conflicts with shields and two-handed
#         if target_slot == EquipmentSlot.OFF_HAND:
#             conflicts.update({EquipmentSlot.BOTH_HANDS, EquipmentSlot.SHIELD})

#         return conflicts

#     @staticmethod
#     def can_equip(character_id: str, equipment_index: str, target_slot: EquipmentSlot, session: Session) -> tuple[bool, str]:
#         # Check if equipment can go in this slot
#         valid_slots = EquipmentValidator.get_valid_slots(equipment_index, session)
#         if target_slot not in valid_slots:
#             return False, f"Equipment cannot be equipped in {target_slot.value} slot"

#         # Check for slot conflicts
#         conflicting_slots = EquipmentValidator.get_conflicting_slots(equipment_index, target_slot, session)

#         current_equipment = session.exec(
#             select(CharacterEquipment)
#             .where(CharacterEquipment.character_id == character_id)
#             .where(CharacterEquipment.equipped_slot.in_(conflicting_slots | {target_slot}))
#         ).all()

#         if current_equipment:
#             equipped_items = [eq.equipment_index for eq in current_equipment]
#             return False, f"Cannot equip: conflicts with {equipped_items}"

#         # Check strength requirements using existing Armor table
#         from your_existing_models import Armor
#         armor = session.exec(
#             select(Armor).where(Armor.equipment_index == equipment_index)
#         ).first()

#         if armor and armor.min_strength:
#             # You'd get character strength from your Character model
#             pass

#         return True, "Can equip"

#     @staticmethod
#     def get_damage_dice(equipment_index: str, equipped_slot: EquipmentSlot, session: Session) -> str:
#         """Get damage dice, accounting for versatile weapons"""
#         from your_existing_models import Weapon

#         weapon = session.exec(
#             select(Weapon).where(Weapon.equipment_index == equipment_index)
#         ).first()

#         if not weapon:
#             return None

#         # If versatile and equipped two-handed, use versatile damage
#         if (equipped_slot == EquipmentSlot.BOTH_HANDS and
#             EquipmentValidator.is_versatile(equipment_index, session) and
#             weapon.versatile_damage_dice):
#             return weapon.versatile_damage_dice

#         return weapon.damage_dice


# def setup_equipment_slots(session: Session):
#     """Setup slot requirements using existing equipment data"""

#     # You'd populate this based on your existing equipment/weapon data
#     # Examples:

#     # Longswords (versatile) can be main hand or both hands
#     session.add(EquipmentSlotRequirement(equipment_index="longsword", slot=EquipmentSlot.MAIN_HAND))
#     session.add(EquipmentSlotRequirement(equipment_index="longsword", slot=EquipmentSlot.BOTH_HANDS))

#     # Daggers (light) can be main hand or off hand
#     session.add(EquipmentSlotRequirement(equipment_index="dagger", slot=EquipmentSlot.MAIN_HAND))
#     session.add(EquipmentSlotRequirement(equipment_index="dagger", slot=EquipmentSlot.OFF_HAND))

#     # Greataxe (two-handed) only both hands
#     session.add(EquipmentSlotRequirement(equipment_index="greataxe", slot=EquipmentSlot.BOTH_HANDS))

#     session.commit()


# Helper functions for JSON field management
def get_json_field(field_value) -> List[str]:
    """Helper to get JSON field as Python list"""
    if not field_value:
        return []
    return json.loads(field_value) if isinstance(field_value, str) else field_value


def set_json_field(field_list: List[str]) -> str:
    """Helper to set JSON field from Python list"""
    return json.dumps(field_list)
