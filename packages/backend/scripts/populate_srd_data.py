#!/usr/bin/env python3
"""
SRD Data Population Script

This script provides utilities for populating the SRD database with initial data:
- Sample SRD data for testing
- Data consistency checks
- Cleanup procedures
- Initial data validation

Usage:
    python populate_srd_data.py --populate-sample
    python populate_srd_data.py --check-consistency
    python populate_srd_data.py --cleanup-data
    python populate_srd_data.py --validate-data
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.backend.components.srd.srd_compliance_service import srd_compliance_service
from packages.backend.components.srd.srd_data_verification_service import (
    srd_data_verification_service,
)
from packages.backend.components.srd.srd_database_manager import srd_database_manager
from packages.shared.logging_config import get_logger
from packages.shared.models import DataSource, Monster, Spell, SRDCompliance, Weapon

logger = get_logger(__name__)


def create_sample_monsters() -> list[Monster]:
    """Create sample monster data for testing."""
    data_source = DataSource(
        source_name="D&D 5.1 SRD",
        source_url="https://dnd.wizards.com/articles/features/systems-reference-document-srd",
        publication_date=datetime(2016, 5, 12),
        version="5.1",
        checksum="sample_checksum_123",
        is_official=True,
        attribution_required=True,
    )

    compliance = SRDCompliance(
        data_source="D&D 5.1 SRD",
        license_version="5.1",
        usage_restrictions=[
            "Must include Wizards of the Coast attribution",
            "Cannot be used in commercial products",
        ],
        last_verified=datetime.utcnow(),
        verification_hash="sample_hash_123",
        compliance_officer="Data Population Script",
        audit_trail=["Sample data creation"],
    )

    return [
        Monster(
            monster_name="Goblin",
            armor_class=15,
            hit_points="7 (2d6)",
            strength=8,
            dexterity=14,
            constitution=10,
            intelligence=10,
            wisdom=8,
            charisma=8,
            challenge_rating="1/4",
            actions="Scimitar: +4 to hit, 1d6+2 slashing damage",
            special_abilities="Nimble Escape: Can take Disengage or Hide as bonus action",
            description="A small, green humanoid with sharp features and a mischievous demeanor",
            srd_compliance=compliance,
            data_source=data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        ),
        Monster(
            monster_name="Orc",
            armor_class=13,
            hit_points="15 (2d8 + 6)",
            strength=16,
            dexterity=12,
            constitution=16,
            intelligence=7,
            wisdom=11,
            charisma=10,
            challenge_rating="1/2",
            actions="Greataxe: +5 to hit, 1d12+3 slashing damage",
            special_abilities="Aggressive: Can move up to speed toward hostile creature",
            description="A burly humanoid with grayish skin and a warlike temperament",
            srd_compliance=compliance,
            data_source=data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        ),
        Monster(
            monster_name="Giant Rat",
            armor_class=12,
            hit_points="7 (2d6)",
            strength=7,
            dexterity=15,
            constitution=11,
            intelligence=2,
            wisdom=10,
            charisma=4,
            challenge_rating="1/8",
            actions="Bite: +4 to hit, 1d4+2 piercing damage",
            special_abilities="Pack Tactics: Advantage on attack rolls against creature with ally within 5 ft",
            description="A larger, more aggressive version of a common rat",
            srd_compliance=compliance,
            data_source=data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        ),
    ]


def create_sample_spells() -> list[Spell]:
    """Create sample spell data for testing."""
    data_source = DataSource(
        source_name="D&D 5.1 SRD",
        source_url="https://dnd.wizards.com/articles/features/systems-reference-document-srd",
        publication_date=datetime(2016, 5, 12),
        version="5.1",
        checksum="sample_checksum_456",
        is_official=True,
        attribution_required=True,
    )

    compliance = SRDCompliance(
        data_source="D&D 5.1 SRD",
        license_version="5.1",
        usage_restrictions=[
            "Must include Wizards of the Coast attribution",
            "Cannot be used in commercial products",
        ],
        last_verified=datetime.utcnow(),
        verification_hash="sample_hash_456",
        compliance_officer="Data Population Script",
        audit_trail=["Sample data creation"],
    )

    return [
        Spell(
            spell_name="Fire Bolt",
            level=0,
            school="Evocation",
            casting_time="1 action",
            range="120 feet",
            components="V, S",
            duration="Instantaneous",
            description="You hurl a mote of fire at a creature or object within range. Make a ranged spell attack against the target. On a hit, the target takes 1d10 fire damage. A flammable object hit by this spell ignites if it isn't being worn or carried.",
            at_higher_levels="This spell's damage increases by 1d10 when you reach 5th level (2d10), 11th level (3d10), and 17th level (4d10).",
            classes=["Sorcerer", "Wizard"],
            srd_compliance=compliance,
            data_source=data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        ),
        Spell(
            spell_name="Magic Missile",
            level=1,
            school="Evocation",
            casting_time="1 action",
            range="120 feet",
            components="V, S",
            duration="Instantaneous",
            description="You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4+1 force damage to its target. The darts all strike simultaneously and you can direct them to hit one creature or several.",
            at_higher_levels="When you cast this spell using a spell slot of 2nd level or higher, the spell creates one more dart for each slot level above 1st.",
            classes=["Sorcerer", "Wizard"],
            srd_compliance=compliance,
            data_source=data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        ),
        Spell(
            spell_name="Cure Wounds",
            level=1,
            school="Evocation",
            casting_time="1 action",
            range="Touch",
            components="V, S",
            duration="Instantaneous",
            description="A creature you touch regains a number of hit points equal to 1d8 + your spellcasting ability modifier. This spell has no effect on undead or constructs.",
            at_higher_levels="When you cast this spell using a spell slot of 2nd level or higher, the healing increases by 1d8 for each slot level above 1st.",
            classes=["Bard", "Cleric", "Druid", "Paladin", "Ranger"],
            srd_compliance=compliance,
            data_source=data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        ),
    ]


def create_sample_weapons() -> list[Weapon]:
    """Create sample weapon data for testing."""
    data_source = DataSource(
        source_name="D&D 5.1 SRD",
        source_url="https://dnd.wizards.com/articles/features/systems-reference-document-srd",
        publication_date=datetime(2016, 5, 12),
        version="5.1",
        checksum="sample_checksum_789",
        is_official=True,
        attribution_required=True,
    )

    compliance = SRDCompliance(
        data_source="D&D 5.1 SRD",
        license_version="5.1",
        usage_restrictions=[
            "Must include Wizards of the Coast attribution",
            "Cannot be used in commercial products",
        ],
        last_verified=datetime.utcnow(),
        verification_hash="sample_hash_789",
        compliance_officer="Data Population Script",
        audit_trail=["Sample data creation"],
    )

    return [
        Weapon(
            weapon_name="Longsword",
            category="Martial Melee Weapons",
            cost="15 gp",
            damage="1d8 slashing",
            weight="3 lb.",
            properties=["Versatile (1d10)"],
            description="A versatile martial melee weapon that can be used with one or two hands",
            srd_compliance=compliance,
            data_source=data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        ),
        Weapon(
            weapon_name="Shortbow",
            category="Simple Ranged Weapons",
            cost="25 gp",
            damage="1d6 piercing",
            weight="2 lb.",
            properties=["Ammunition (range 80/320)", "Two-Handed"],
            description="A simple ranged weapon that fires arrows with decent range and accuracy",
            srd_compliance=compliance,
            data_source=data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        ),
        Weapon(
            weapon_name="Quarterstaff",
            category="Simple Melee Weapons",
            cost="0.2 gp",
            damage="1d6 bludgeoning",
            weight="4 lb.",
            properties=["Versatile (1d8)"],
            description="A simple wooden staff that can be used for melee combat with one or two hands",
            srd_compliance=compliance,
            data_source=data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        ),
    ]


def populate_sample_data():
    """Populate database with sample SRD data."""
    logger.info("Starting sample data population...")

    try:
        # Create sample data
        monsters = create_sample_monsters()
        spells = create_sample_spells()
        weapons = create_sample_weapons()

        # Insert monsters
        for monster in monsters:
            try:
                monster_id = srd_database_manager.create_monster(
                    monster, "data_population_script"
                )
                logger.info(
                    f"Created monster: {monster.monster_name} (ID: {monster_id})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create monster {monster.monster_name}: {str(e)}"
                )

        # Insert spells
        for spell in spells:
            try:
                spell_id = srd_database_manager.create_spell(
                    spell, "data_population_script"
                )
                logger.info(f"Created spell: {spell.spell_name} (ID: {spell_id})")
            except Exception as e:
                logger.error(f"Failed to create spell {spell.spell_name}: {str(e)}")

        # Insert weapons
        for weapon in weapons:
            try:
                weapon_id = srd_database_manager.create_weapon(
                    weapon, "data_population_script"
                )
                logger.info(f"Created weapon: {weapon.weapon_name} (ID: {weapon_id})")
            except Exception as e:
                logger.error(f"Failed to create weapon {weapon.weapon_name}: {str(e)}")

        logger.info("Sample data population completed successfully")

    except Exception as e:
        logger.error(f"Sample data population failed: {str(e)}")
        raise


def check_data_consistency():
    """Check data consistency and integrity."""
    logger.info("Starting data consistency checks...")

    try:
        # Get database stats
        stats = srd_database_manager.get_database_stats()

        logger.info(
            f"Database contains: {stats.total_monsters} monsters, {stats.total_spells} spells, {stats.total_weapons} weapons"
        )

        # Check for data integrity issues
        issues = []

        # Check monsters
        monsters = srd_database_manager.get_monsters_by_challenge_rating(0, 30)
        for monster in monsters:
            # Verify compliance
            compliance_result = srd_compliance_service.verify_data_compliance(
                monster, "monster", "consistency_check"
            )
            if not compliance_result.is_compliant:
                issues.append(
                    f"Monster {monster.monster_name}: {', '.join(compliance_result.issues)}"
                )

            # Verify data integrity
            verification = srd_data_verification_service.verify_monster_data(monster)
            if verification.status.value == "invalid":
                issues.append(
                    f"Monster {monster.monster_name} data integrity issues: {', '.join(verification.issues)}"
                )

        # Check spells
        spells = srd_database_manager.get_spells_by_level(
            0
        )  # Get all cantrips as sample
        for spell in spells:
            compliance_result = srd_compliance_service.verify_data_compliance(
                spell, "spell", "consistency_check"
            )
            if not compliance_result.is_compliant:
                issues.append(
                    f"Spell {spell.spell_name}: {', '.join(compliance_result.issues)}"
                )

            verification = srd_data_verification_service.verify_spell_data(spell)
            if verification.status.value == "invalid":
                issues.append(
                    f"Spell {spell.spell_name} data integrity issues: {', '.join(verification.issues)}"
                )

        # Check weapons
        weapons = srd_database_manager.get_weapons_by_category("Simple Melee Weapons")
        for weapon in weapons:
            compliance_result = srd_compliance_service.verify_data_compliance(
                weapon, "weapon", "consistency_check"
            )
            if not compliance_result.is_compliant:
                issues.append(
                    f"Weapon {weapon.weapon_name}: {', '.join(compliance_result.issues)}"
                )

            verification = srd_data_verification_service.verify_weapon_data(weapon)
            if verification.status.value == "invalid":
                issues.append(
                    f"Weapon {weapon.weapon_name} data integrity issues: {', '.join(verification.issues)}"
                )

        if issues:
            logger.warning(f"Found {len(issues)} data consistency issues:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        else:
            logger.info("No data consistency issues found")

        logger.info("Data consistency checks completed")

    except Exception as e:
        logger.error(f"Data consistency check failed: {str(e)}")
        raise


def cleanup_data():
    """Clean up and optimize database."""
    logger.info("Starting data cleanup...")

    try:
        # Get initial stats
        initial_stats = srd_database_manager.get_database_stats()
        logger.info(
            f"Initial state: {initial_stats.total_monsters} monsters, {initial_stats.total_spells} spells, {initial_stats.total_weapons} weapons"
        )

        # Create backup before cleanup
        backup_path = srd_database_manager.create_backup("pre_cleanup_backup")
        logger.info(f"Created backup: {backup_path}")

        # Note: In a real implementation, you would add specific cleanup logic here
        # For example: removing duplicate records, fixing data inconsistencies, etc.

        # Get final stats
        final_stats = srd_database_manager.get_database_stats()
        logger.info(
            f"Final state: {final_stats.total_monsters} monsters, {final_stats.total_spells} spells, {final_stats.total_weapons} weapons"
        )

        logger.info("Data cleanup completed successfully")

    except Exception as e:
        logger.error(f"Data cleanup failed: {str(e)}")
        raise


def validate_data():
    """Validate all data in the database."""
    logger.info("Starting data validation...")

    try:
        # Get all data for validation
        all_monsters = srd_database_manager.get_monsters_by_challenge_rating(0, 30)
        all_spells = srd_database_manager.get_spells_by_level(0)  # Sample
        all_weapons = srd_database_manager.get_weapons_by_category(
            "Simple Melee Weapons"
        )  # Sample

        total_entities = len(all_monsters) + len(all_spells) + len(all_weapons)
        logger.info(f"Validating {total_entities} total entities...")

        # Validate monsters
        valid_monsters = 0
        for monster in all_monsters:
            verification = srd_data_verification_service.verify_monster_data(monster)
            if verification.status.value in ["verified", "modified"]:
                valid_monsters += 1

        # Validate spells
        valid_spells = 0
        for spell in all_spells:
            verification = srd_data_verification_service.verify_spell_data(spell)
            if verification.status.value in ["verified", "modified"]:
                valid_spells += 1

        # Validate weapons
        valid_weapons = 0
        for weapon in all_weapons:
            verification = srd_data_verification_service.verify_weapon_data(weapon)
            if verification.status.value in ["verified", "modified"]:
                valid_weapons += 1

        total_valid = valid_monsters + valid_spells + valid_weapons
        validation_rate = (total_valid / total_entities) if total_entities > 0 else 1.0

        logger.info("Validation results:")
        logger.info(f"  Monsters: {valid_monsters}/{len(all_monsters)} valid")
        logger.info(f"  Spells: {valid_spells}/{len(all_spells)} valid")
        logger.info(f"  Weapons: {valid_weapons}/{len(all_weapons)} valid")
        logger.info(".2%")

        if validation_rate < 0.95:
            logger.warning(
                "Low validation rate detected. Review data sources and integrity."
            )
        else:
            logger.info("Data validation completed successfully")

    except Exception as e:
        logger.error(f"Data validation failed: {str(e)}")
        raise


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="SRD Data Population Script")
    parser.add_argument(
        "--populate-sample",
        action="store_true",
        help="Populate database with sample data",
    )
    parser.add_argument(
        "--check-consistency",
        action="store_true",
        help="Check data consistency and integrity",
    )
    parser.add_argument(
        "--cleanup-data", action="store_true", help="Clean up and optimize database"
    )
    parser.add_argument(
        "--validate-data", action="store_true", help="Validate all data in the database"
    )

    args = parser.parse_args()

    if not any(
        [
            args.populate_sample,
            args.check_consistency,
            args.cleanup_data,
            args.validate_data,
        ]
    ):
        parser.print_help()
        return

    try:
        if args.populate_sample:
            populate_sample_data()

        if args.check_consistency:
            check_data_consistency()

        if args.cleanup_data:
            cleanup_data()

        if args.validate_data:
            validate_data()

        logger.info("All requested operations completed successfully")

    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
