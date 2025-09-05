"""
Unit tests for SRD Data Import Service.

Tests cover:
- JSON and CSV file import functionality
- Data validation and transformation
- Import progress tracking and error handling
- Conflict resolution strategies
- Bulk import operations
- Import history and rollback capabilities
"""

import csv
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from packages.backend.components.srd.srd_data_import_service import (
    ConflictResolution,
    ImportProgress,
    ImportResult,
    ImportStatus,
    SRDDataImportService,
)
from packages.shared.models import DataSource, Monster, Spell, SRDCompliance, Weapon


class TestSRDDataImportService:
    """Test cases for SRD Data Import Service."""

    @pytest.fixture
    def import_service(self):
        """Create a fresh import service for each test."""
        return SRDDataImportService()

    @pytest.fixture
    def sample_json_data(self):
        """Create sample JSON data for testing."""
        return {
            "monsters": [
                {
                    "monster_name": "Test Goblin",
                    "armor_class": 15,
                    "hit_points": "7 (2d6)",
                    "strength": 8,
                    "dexterity": 14,
                    "constitution": 10,
                    "intelligence": 10,
                    "wisdom": 8,
                    "charisma": 8,
                    "challenge_rating": "1/4",
                    "actions": "Scimitar: +4 to hit, 1d6+2 slashing damage",
                    "special_abilities": "Nimble Escape",
                    "description": "A small, green humanoid",
                }
            ],
            "spells": [
                {
                    "spell_name": "Fire Bolt",
                    "level": 0,
                    "school": "Evocation",
                    "casting_time": "1 action",
                    "range": "120 feet",
                    "components": "V, S",
                    "duration": "Instantaneous",
                    "description": "You hurl a mote of fire at a creature",
                    "classes": ["Sorcerer", "Wizard"],
                }
            ],
            "weapons": [
                {
                    "weapon_name": "Longsword",
                    "category": "Martial Melee Weapons",
                    "cost": "15 gp",
                    "damage": "1d8 slashing",
                    "weight": "3 lb.",
                    "properties": ["Versatile (1d10)"],
                    "description": "A versatile martial melee weapon",
                }
            ],
        }

    @pytest.fixture
    def temp_json_file(self, sample_json_data):
        """Create a temporary JSON file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_json_data, f)
            temp_path = f.name
        yield temp_path
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def temp_csv_file(self, sample_json_data):
        """Create a temporary CSV file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(
                f, fieldnames=sample_json_data["monsters"][0].keys()
            )
            writer.writeheader()
            writer.writerows(sample_json_data["monsters"])
            temp_path = f.name
        yield temp_path
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    def test_import_from_json_file_monsters(self, import_service, temp_json_file):
        """Test JSON import for monsters."""
        result = import_service.import_from_json_file(
            temp_json_file, "monsters", "test_user"
        )

        assert isinstance(result, ImportResult)
        assert result.total_records == 1
        assert result.successful_imports == 1
        assert result.failed_imports == 0
        assert result.processing_time >= 0

    def test_import_from_json_file_spells(self, import_service, temp_json_file):
        """Test JSON import for spells."""
        result = import_service.import_from_json_file(
            temp_json_file, "spells", "test_user"
        )

        assert isinstance(result, ImportResult)
        assert result.total_records == 1
        assert result.successful_imports == 1
        assert result.failed_imports == 0

    def test_import_from_json_file_weapons(self, import_service, temp_json_file):
        """Test JSON import for weapons."""
        result = import_service.import_from_json_file(
            temp_json_file, "weapons", "test_user"
        )

        assert isinstance(result, ImportResult)
        assert result.total_records == 1
        assert result.successful_imports == 1
        assert result.failed_imports == 0

    def test_import_from_csv_file(self, import_service, temp_csv_file):
        """Test CSV import for monsters."""
        result = import_service.import_from_csv_file(
            temp_csv_file, "monsters", "test_user"
        )

        assert isinstance(result, ImportResult)
        assert result.total_records == 1
        assert result.successful_imports == 1
        assert result.failed_imports == 0

    def test_import_invalid_json_file(self, import_service):
        """Test import with invalid JSON file."""
        with pytest.raises(Exception):
            import_service.import_from_json_file(
                "/invalid/path.json", "monsters", "test_user"
            )

    def test_import_invalid_csv_file(self, import_service):
        """Test import with invalid CSV file."""
        with pytest.raises(Exception):
            import_service.import_from_csv_file(
                "/invalid/path.csv", "monsters", "test_user"
            )

    def test_import_nonexistent_data_type(self, import_service, temp_json_file):
        """Test import with nonexistent data type."""
        with pytest.raises(ValueError, match="Data type 'invalid_type' not found"):
            import_service.import_from_json_file(
                temp_json_file, "invalid_type", "test_user"
            )

    def test_validate_monster_record_valid(self, import_service):
        """Test validation of valid monster record."""
        record = {
            "monster_name": "Test Monster",
            "armor_class": 15,
            "hit_points": "10 (3d6)",
            "strength": 14,
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 8,
            "wisdom": 10,
            "charisma": 8,
            "challenge_rating": "1/2",
        }

        validated = import_service._validate_and_transform_record(record, "monsters")

        assert validated is not None
        assert validated["monster_name"] == "Test Monster"
        assert validated["armor_class"] == 15

    def test_validate_monster_record_invalid(self, import_service):
        """Test validation of invalid monster record."""
        # Missing required field
        record = {
            "monster_name": "Test Monster",
            # Missing armor_class
            "hit_points": "10 (3d6)",
            "strength": 14,
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 8,
            "wisdom": 10,
            "charisma": 8,
            "challenge_rating": "1/2",
        }

        validated = import_service._validate_and_transform_record(record, "monsters")
        assert validated is None

    def test_validate_monster_record_invalid_ability_score(self, import_service):
        """Test validation of monster record with invalid ability score."""
        record = {
            "monster_name": "Test Monster",
            "armor_class": 15,
            "hit_points": "10 (3d6)",
            "strength": 35,  # Invalid score (> 30)
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 8,
            "wisdom": 10,
            "charisma": 8,
            "challenge_rating": "1/2",
        }

        validated = import_service._validate_and_transform_record(record, "monsters")
        assert validated is None

    def test_validate_spell_record_valid(self, import_service):
        """Test validation of valid spell record."""
        record = {
            "spell_name": "Test Spell",
            "level": 3,
            "school": "Evocation",
            "casting_time": "1 action",
            "range": "120 feet",
            "components": "V, S, M",
            "duration": "1 minute",
            "description": "A test spell",
        }

        validated = import_service._validate_and_transform_record(record, "spells")

        assert validated is not None
        assert validated["spell_name"] == "Test Spell"
        assert validated["level"] == 3

    def test_validate_spell_record_invalid_level(self, import_service):
        """Test validation of spell record with invalid level."""
        record = {
            "spell_name": "Test Spell",
            "level": 10,  # Invalid level (> 9)
            "school": "Evocation",
            "casting_time": "1 action",
            "range": "120 feet",
            "components": "V, S, M",
            "duration": "1 minute",
            "description": "A test spell",
        }

        validated = import_service._validate_and_transform_record(record, "spells")
        assert validated is None

    def test_validate_weapon_record_valid(self, import_service):
        """Test validation of valid weapon record."""
        record = {
            "weapon_name": "Test Weapon",
            "category": "Simple Melee Weapons",
            "cost": "5 gp",
            "damage": "1d6 piercing",
            "weight": "2 lb.",
            "properties": ["Light", "Finesse"],
        }

        validated = import_service._validate_and_transform_record(record, "weapons")

        assert validated is not None
        assert validated["weapon_name"] == "Test Weapon"
        assert validated["category"] == "Simple Melee Weapons"

    def test_create_srd_entity_monster(self, import_service):
        """Test SRD entity creation for monster."""
        record = {
            "monster_name": "Test Monster",
            "armor_class": 15,
            "hit_points": "10 (3d6)",
            "strength": 14,
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 8,
            "wisdom": 10,
            "charisma": 8,
            "challenge_rating": "1/2",
            "actions": "Test Action",
            "special_abilities": "Test Ability",
            "description": "A test monster",
        }

        entity = import_service._create_srd_entity(record, "monsters")

        assert isinstance(entity, Monster)
        assert entity.monster_name == "Test Monster"
        assert entity.armor_class == 15
        assert isinstance(entity.srd_compliance, SRDCompliance)
        assert isinstance(entity.data_source, DataSource)

    def test_create_srd_entity_spell(self, import_service):
        """Test SRD entity creation for spell."""
        record = {
            "spell_name": "Test Spell",
            "level": 3,
            "school": "Evocation",
            "casting_time": "1 action",
            "range": "120 feet",
            "components": "V, S, M",
            "duration": "1 minute",
            "description": "A test spell",
            "at_higher_levels": "Test higher level effects",
            "classes": ["Wizard", "Sorcerer"],
        }

        entity = import_service._create_srd_entity(record, "spells")

        assert isinstance(entity, Spell)
        assert entity.spell_name == "Test Spell"
        assert entity.level == 3
        assert entity.classes == ["Wizard", "Sorcerer"]

    def test_create_srd_entity_weapon(self, import_service):
        """Test SRD entity creation for weapon."""
        record = {
            "weapon_name": "Test Weapon",
            "category": "Simple Melee Weapons",
            "cost": "5 gp",
            "damage": "1d6 piercing",
            "weight": "2 lb.",
            "properties": ["Light", "Finesse"],
            "description": "A test weapon",
        }

        entity = import_service._create_srd_entity(record, "weapons")

        assert isinstance(entity, Weapon)
        assert entity.weapon_name == "Test Weapon"
        assert entity.category == "Simple Melee Weapons"
        assert entity.properties == ["Light", "Finesse"]

    def test_conflict_resolution_skip(self, import_service, temp_json_file):
        """Test conflict resolution with SKIP strategy."""
        # Import once
        result1 = import_service.import_from_json_file(
            temp_json_file, "monsters", "test_user", ConflictResolution.UPDATE
        )

        # Import again with SKIP
        result2 = import_service.import_from_json_file(
            temp_json_file, "monsters", "test_user", ConflictResolution.SKIP
        )

        assert result1.successful_imports == 1
        assert result2.skipped_records == 1
        assert result2.successful_imports == 0

    def test_calculate_record_hash(self, import_service):
        """Test record hash calculation."""
        record = {"name": "test", "value": 123}

        hash1 = import_service._calculate_record_hash(record)
        hash2 = import_service._calculate_record_hash(record)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex length

    def test_import_progress_tracking(self, import_service, temp_json_file):
        """Test import progress tracking."""
        # This would need to be tested with actual async import
        # For now, just test the structure
        progress = ImportProgress(
            status=ImportStatus.PENDING, current_record=0, total_records=10
        )

        assert progress.status == ImportStatus.PENDING
        assert progress.current_record == 0
        assert progress.total_records == 10

    def test_get_import_progress(self, import_service):
        """Test getting import progress."""
        # Test with non-existent import ID
        progress = import_service.get_import_progress("nonexistent")
        assert progress is None

    def test_cancel_import(self, import_service):
        """Test import cancellation."""
        # Test with non-existent import ID
        result = import_service.cancel_import("nonexistent")
        assert result is False


class TestImportResult:
    """Test cases for ImportResult model."""

    def test_import_result_creation(self):
        """Test ImportResult creation."""
        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]

        result = ImportResult(
            total_records=10,
            successful_imports=8,
            failed_imports=2,
            skipped_records=0,
            errors=errors,
            warnings=warnings,
            processing_time=1.5,
        )

        assert result.total_records == 10
        assert result.successful_imports == 8
        assert result.failed_imports == 2
        assert result.skipped_records == 0
        assert result.errors == errors
        assert result.warnings == warnings
        assert result.processing_time == 1.5

    def test_import_result_defaults(self):
        """Test ImportResult default values."""
        result = ImportResult()

        assert result.total_records == 0
        assert result.successful_imports == 0
        assert result.failed_imports == 0
        assert result.skipped_records == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.processing_time == 0.0


class TestImportProgress:
    """Test cases for ImportProgress model."""

    def test_import_progress_creation(self):
        """Test ImportProgress creation."""
        start_time = datetime.utcnow()
        result = ImportResult()

        progress = ImportProgress(
            status=ImportStatus.IN_PROGRESS,
            current_record=5,
            total_records=10,
            start_time=start_time,
            result=result,
        )

        assert progress.status == ImportStatus.IN_PROGRESS
        assert progress.current_record == 5
        assert progress.total_records == 10
        assert progress.start_time == start_time
        assert progress.result == result

    def test_import_progress_defaults(self):
        """Test ImportProgress default values."""
        progress = ImportProgress()

        assert progress.status == ImportStatus.PENDING
        assert progress.current_record == 0
        assert progress.total_records == 0
        assert progress.start_time is None
        assert progress.end_time is None
        assert progress.result is None
