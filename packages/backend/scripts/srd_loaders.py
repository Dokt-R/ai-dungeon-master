import json
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.db import get_async_session
from packages.shared.models.game.equipment_models import (
    Armor,
    DamageType,
    Equipment,
    EquipmentCategory,
    EquipmentPackContent,
    EquipmentSlot,
    EquipmentSlotRequirement,
    EquipmentWeaponProperty,  # Added this import
    Gear,
    MountAndVehicle,
    Tool,
    Weapon,
    WeaponProperty,
)


async def load_srd_data(session: AsyncSession, srd_json_path: str = "srd/json_files"):
    """
    Loads SRD equipment data from JSON files into the database.
    """
    print(f"Loading SRD data from {srd_json_path}...")

    # Load JSON data
    with open(f"{srd_json_path}/damage_types.json", "r") as f:
        damage_types_data = json.load(f)
    with open(f"{srd_json_path}/weapon_properties.json", "r") as f:
        weapon_properties_data = json.load(f)
    with open(f"{srd_json_path}/equipment_categories.json", "r") as f:
        equipment_categories_data = json.load(f)
    with open(f"{srd_json_path}/equipment.json", "r") as f:
        equipment_data = json.load(f)

    # --- Load Damage Types ---
    damage_type_map: Dict[str, DamageType] = {}
    for dt_data in damage_types_data:
        damage_type = DamageType(**dt_data)
        session.add(damage_type)
        damage_type_map[damage_type.index] = damage_type
    await session.commit()
    print(f"Loaded {len(damage_type_map)} damage types.")

    # --- Load Weapon Properties ---
    weapon_property_map: Dict[str, WeaponProperty] = {}
    for wp_data in weapon_properties_data:
        weapon_property = WeaponProperty(**wp_data)
        session.add(weapon_property)
        weapon_property_map[weapon_property.index] = weapon_property
    await session.commit()
    print(f"Loaded {len(weapon_property_map)} weapon properties.")

    # --- Load Equipment Categories ---
    equipment_category_map: Dict[str, EquipmentCategory] = {}
    for ec_data in equipment_categories_data:
        # Exclude the 'equipment' list as it's a relationship and will be populated later
        ec_dict = {k: v for k, v in ec_data.items() if k != "equipment"}
        equipment_category = EquipmentCategory(**ec_dict)
        session.add(equipment_category)
        equipment_category_map[equipment_category.index] = equipment_category
    await session.commit()
    print(f"Loaded {len(equipment_category_map)} equipment categories.")

    # --- Load Equipment and its specific types ---
    for item_data in equipment_data:
        # Basic Equipment fields
        equipment_category_index = item_data["equipment_category"]["index"]
        equipment_category = equipment_category_map.get(equipment_category_index)

        if not equipment_category:
            print(
                f"Warning: Equipment category '{equipment_category_index}' not found for {item_data['name']}. Skipping."
            )
            continue

        cost_data = item_data.get("cost")
        cost_quantity = cost_data.get("quantity") if cost_data else None
        cost_unit = cost_data.get("unit") if cost_data else None

        equipment = Equipment(
            index=item_data["index"],
            name=item_data["name"],
            url=item_data["url"],
            equipment_category_index=equipment_category_index,
            cost_quantity=cost_quantity,
            cost_unit=cost_unit,
            weight=item_data.get("weight"),
            special=item_data.get("special"),
            desc=item_data.get("desc"),
        )
        session.add(equipment)
        session.flush()  # Flush to get the equipment.index for relationships

        # Handle specific equipment types
        if equipment_category_index == "weapon":
            damage_type_index = (
                item_data["damage"]["damage_type"]["index"]
                if item_data.get("damage") and item_data["damage"].get("damage_type")
                else None
            )
            damage_dice = item_data["damage"].get("damage_dice")

            # Handle versatile damage
            versatile_damage_data = item_data.get("two_handed_damage")
            versatile_damage_dice = None
            versatile_damage_type_index = None
            if versatile_damage_data:
                versatile_damage_dice = versatile_damage_data.get("damage_dice")
                versatile_damage_type_index = versatile_damage_data.get(
                    "damage_type", {}
                ).get("index")

            weapon = Weapon(
                equipment_index=equipment.index,
                weapon_category=item_data.get("weapon_category"),
                category_range=item_data.get("category_range"),
                damage_dice=damage_dice,
                damage_type_index=damage_type_index,
                versatile_damage_dice=versatile_damage_dice,
                versatile_damage_type_index=versatile_damage_type_index,
                weapon_range=item_data.get("weapon_range"),
                range_normal=item_data.get("range", {}).get("normal"),
                range_long=item_data.get("range", {}).get("long"),
                throw_range_normal=item_data.get("throw_range", {}).get("normal"),
                throw_range_long=item_data.get("throw_range", {}).get("long"),
            )
            session.add(weapon)

            # Add weapon properties
            for prop_data in item_data.get("properties", []):
                # Ensure the property exists in our map before creating the link
                if prop_data["index"] in weapon_property_map:
                    equipment_weapon_property = EquipmentWeaponProperty(
                        equipment_index=equipment.index,
                        weapon_property_index=prop_data["index"],
                    )
                    session.add(equipment_weapon_property)
                else:
                    print(
                        f"Warning: Weapon property '{prop_data['index']}' not found for {equipment.name}. Skipping link."
                    )

            # Add EquipmentSlotRequirement for weapons
            if "two-handed" in [p["index"] for p in item_data.get("properties", [])]:
                session.add(
                    EquipmentSlotRequirement(
                        equipment_index=equipment.index,
                        slot=EquipmentSlot.BOTH_HANDS,
                        is_primary=True,
                    )
                )
            elif "versatile" in [p["index"] for p in item_data.get("properties", [])]:
                session.add(
                    EquipmentSlotRequirement(
                        equipment_index=equipment.index,
                        slot=EquipmentSlot.MAIN_HAND,
                        is_primary=True,
                    )
                )
                session.add(
                    EquipmentSlotRequirement(
                        equipment_index=equipment.index,
                        slot=EquipmentSlot.BOTH_HANDS,
                        is_primary=False,
                    )
                )
            else:
                session.add(
                    EquipmentSlotRequirement(
                        equipment_index=equipment.index,
                        slot=EquipmentSlot.MAIN_HAND,
                        is_primary=True,
                    )
                )
                if "light" in [p["index"] for p in item_data.get("properties", [])]:
                    session.add(
                        EquipmentSlotRequirement(
                            equipment_index=equipment.index,
                            slot=EquipmentSlot.OFF_HAND,
                            is_primary=False,
                        )
                    )

        elif equipment_category_index == "armor":
            armor_class_data = item_data.get("armor_class", {})
            armor = Armor(
                equipment_index=equipment.index,
                armor_category=item_data["armor_category"],
                armor_class_base=armor_class_data.get("base"),
                dex_bonus=armor_class_data.get("dex_bonus", False),
                max_dex_bonus=armor_class_data.get("max_bonus"),
                min_strength=item_data.get("str_minimum", 0),
                stealth_disadvantage=item_data.get("stealth_disadvantage", False),
            )
            session.add(armor)
            session.add(
                EquipmentSlotRequirement(
                    equipment_index=equipment.index,
                    slot=EquipmentSlot.ARMOR,
                    is_primary=True,
                )
            )
            if item_data["armor_category"] == "Shield":
                session.add(
                    EquipmentSlotRequirement(
                        equipment_index=equipment.index,
                        slot=EquipmentSlot.SHIELD,
                        is_primary=True,
                    )
                )

        elif equipment_category_index == "adventuring-gear":
            # Check if it's an equipment pack
            if "contents" in item_data:
                # This is an Equipment Pack, handle its contents
                for content_item in item_data["contents"]:
                    item_index = content_item["item"]["index"]
                    quantity = content_item["quantity"]
                    # We need to ensure the item_index exists as an Equipment before linking
                    # For now, we'll assume it will be loaded later or exists.
                    # A more robust solution would pre-process all equipment first.
                    pack_content = EquipmentPackContent(
                        pack_index=equipment.index,
                        item_index=item_index,
                        quantity=quantity,
                    )
                    session.add(pack_content)
            else:
                # Standard adventuring gear
                gear = Gear(
                    equipment_index=equipment.index,
                    gear_category=item_data.get("gear_category", {}).get("name"),
                    quantity=item_data.get(
                        "quantity", 1
                    ),  # async Default to 1 if not specified
                )
                session.add(gear)

        elif equipment_category_index == "tools":
            tool = Tool(
                equipment_index=equipment.index,
                tool_category=item_data["tool_category"],
            )
            session.add(tool)

        elif equipment_category_index == "mounts-and-vehicles":
            speed_data = item_data.get("speed", {})
            mount_vehicle = MountAndVehicle(
                equipment_index=equipment.index,
                vehicle_category=item_data["vehicle_category"],
                speed_quantity=speed_data.get("quantity"),
                speed_unit=speed_data.get("unit"),
                capacity=item_data.get("capacity"),
                crew_min=item_data.get("crew_min"),
                crew_max=item_data.get("crew_max"),
                engers=item_data.get("engers"),
                ac=item_data.get("ac"),
                hp=item_data.get("hp"),
                damage_threshold=item_data.get("damage_threshold"),
            )
            session.add(mount_vehicle)

        await session.commit()  # Commit each equipment item and its related data

    print("SRD data loading complete.")


if __name__ == "__main__":
    # Example usage:
    # This part would typically be run as a script to populate the database
    # rather than directly from equipment_models.py
    # engine = create_engine("sqlite:///srd_database.sqlite")
    # SQLModel.metadata.create_all(engine)

    with get_async_session() as session:
        load_srd_data(session)
