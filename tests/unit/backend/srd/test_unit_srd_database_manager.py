"""
Unit tests for SRD Database Manager.

Tests cover:
- Database initialization and schema creation
- CRUD operations for monsters, spells, and weapons
- Query operations and filtering
- Backup and recovery procedures
- Health status and statistics
- Error handling and edge cases
"""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from packages.backend.components.srd_database_manager import (
    DatabaseStats,
    SRDDatabaseManager,
)
from packages.shared.models import DataSource, Monster, Spell, SRDCompliance, Weapon


class TestSRDDatabaseManager:
    """Test cases for SRD Database Manager."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Force garbage collection to close any lingering connections
        import gc
        gc.collect()
        # Small delay to ensure file handles are released
        import time
        time.sleep(0.1)
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a database manager with temporary database."""
        manager = SRDDatabaseManager(temp_db_path)
        yield manager
        # Ensure proper cleanup
        import gc
        gc.collect()

    @pytest.fixture
    def sample_data_source(self):
        """Create a sample data source for testing."""
        return DataSource(
            source_name="D&D 5.1 SRD",
            source_url="https://dnd.wizards.com/articles/features/systems-reference-document-srd",
            publication_date=datetime(2016, 5, 12),
            version="5.1",
            checksum="test_checksum_123",
            is_official=True,
            attribution_required=True,
        )

    @pytest.fixture
    def sample_compliance(self):
        """Create a sample compliance record for testing."""
        return SRDCompliance(
            data_source="D&D 5.1 SRD",
            license_version="5.1",
            usage_restrictions=[
                "Must include Wizards of the Coast attribution",
                "Cannot be used in commercial products",
            ],
            last_verified=datetime.utcnow(),
            verification_hash="test_hash_123",
            compliance_officer="Test Officer",
            audit_trail=[
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "initial_import",
                    "user": "Test Officer",
                    "details": "Initial import for testing"
                }
            ],
        )

    @pytest.fixture
    def sample_monster(self, sample_compliance, sample_data_source):
        """Create a sample monster for testing."""
        return Monster(
            monster_name="Test Goblin",
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
            description="A small, green humanoid with sharp features",
            srd_compliance=sample_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

    def test_database_initialization(self, temp_db_path):
        """Test database initialization and schema creation."""
        manager = SRDDatabaseManager(temp_db_path)

        # Check that database file exists
        assert Path(temp_db_path).exists()

        # Check that tables were created
        with manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {"monsters", "spells", "weapons", "database_metadata"}
        assert expected_tables.issubset(tables)

    def test_create_monster(self, db_manager, sample_monster):
        """Test monster creation."""
        monster_id = db_manager.create_monster(sample_monster, "test_user")

        assert isinstance(monster_id, int)
        assert monster_id > 0

        # Verify monster was created
        retrieved_monster = db_manager.get_monster(monster_id)
        assert retrieved_monster is not None
        assert retrieved_monster.monster_name == sample_monster.monster_name
        assert retrieved_monster.armor_class == sample_monster.armor_class

    def test_create_spell(self, db_manager, sample_compliance, sample_data_source):
        """Test spell creation."""
        spell = Spell(
            spell_name="Fire Bolt",
            level=0,
            school="Evocation",
            casting_time="1 action",
            range="120 feet",
            components="V, S",
            duration="Instantaneous",
            description="You hurl a mote of fire at a creature within range",
            at_higher_levels="",
            classes=["Sorcerer", "Wizard"],
            srd_compliance=sample_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        spell_id = db_manager.create_spell(spell, "test_user")

        assert isinstance(spell_id, int)
        assert spell_id > 0

    def test_create_weapon(self, db_manager, sample_compliance, sample_data_source):
        """Test weapon creation."""
        weapon = Weapon(
            weapon_name="Longsword",
            category="Martial Melee Weapons",
            cost="15 gp",
            damage="1d8 slashing",
            weight="3 lb.",
            properties=["Versatile (1d10)"],
            description="A versatile martial melee weapon",
            srd_compliance=sample_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        weapon_id = db_manager.create_weapon(weapon, "test_user")

        assert isinstance(weapon_id, int)
        assert weapon_id > 0

    def test_get_monsters_by_challenge_rating(self, db_manager, sample_monster):
        """Test getting monsters by challenge rating range."""
        # Create the monster first
        db_manager.create_monster(sample_monster, "test_user")

        # Query monsters by CR
        monsters = db_manager.get_monsters_by_challenge_rating(0.0, 1.0)

        assert isinstance(monsters, list)
        assert len(monsters) > 0
        assert monsters[0].monster_name == sample_monster.monster_name

    def test_get_spells_by_level(
        self, db_manager, sample_compliance, sample_data_source
    ):
        """Test getting spells by level."""
        spell = Spell(
            spell_name="Fire Bolt",
            level=0,
            school="Evocation",
            casting_time="1 action",
            range="120 feet",
            components="V, S",
            duration="Instantaneous",
            description="You hurl a mote of fire at a creature within range",
            at_higher_levels="",
            classes=["Sorcerer", "Wizard"],
            srd_compliance=sample_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        # Create the spell first
        db_manager.create_spell(spell, "test_user")

        # Query spells by level
        spells = db_manager.get_spells_by_level(0)

        assert isinstance(spells, list)
        assert len(spells) > 0
        assert spells[0].spell_name == spell.spell_name
        assert spells[0].level == 0

    def test_get_weapons_by_category(
        self, db_manager, sample_compliance, sample_data_source
    ):
        """Test getting weapons by category."""
        weapon = Weapon(
            weapon_name="Longsword",
            category="Martial Melee Weapons",
            cost="15 gp",
            damage="1d8 slashing",
            weight="3 lb.",
            properties=["Versatile (1d10)"],
            description="A versatile martial melee weapon",
            srd_compliance=sample_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        # Create the weapon first
        db_manager.create_weapon(weapon, "test_user")

        # Query weapons by category
        weapons = db_manager.get_weapons_by_category("Martial Melee Weapons")

        assert isinstance(weapons, list)
        assert len(weapons) > 0
        assert weapons[0].weapon_name == weapon.weapon_name
        assert weapons[0].category == weapon.category

    def test_create_backup(self, db_manager):
        """Test database backup creation."""
        backup_path = db_manager.create_backup()

        assert isinstance(backup_path, str)
        assert Path(backup_path).exists()
        assert Path(backup_path).stat().st_size > 0

    def test_get_database_stats(self, db_manager, sample_monster):
        """Test database statistics retrieval."""
        # Create a monster to have some data
        db_manager.create_monster(sample_monster, "test_user")

        stats = db_manager.get_database_stats()

        assert isinstance(stats, DatabaseStats)
        assert stats.total_monsters >= 1
        assert stats.database_size > 0
        assert stats.schema_version == "1.0"
        assert stats.connection_healthy is True

    def test_get_health_status(self, db_manager):
        """Test health status retrieval."""
        health = db_manager.get_health_status()

        assert isinstance(health, dict)
        assert "status" in health
        assert "database_exists" in health
        assert "database_path" in health
        assert "total_monsters" in health

    def test_invalid_monster_creation(self, db_manager, sample_monster):
        """Test error handling for invalid monster creation."""
        # Create a monster with invalid ability score
        sample_monster.strength = 50  # Invalid score (> 30)

        with pytest.raises(ValueError, match="Invalid strength score: 50"):
            db_manager.create_monster(sample_monster, "test_user")

    def test_database_connection_error(self, temp_db_path):
        """Test database connection error handling."""
        import tempfile
        from unittest.mock import patch, MagicMock

        # Create a temporary database manager
        manager = SRDDatabaseManager(temp_db_path)

        # Mock sqlite3.connect to raise an exception
        with patch('packages.backend.components.srd_database_manager.sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Connection failed")

            # Test that get_health_status handles connection errors gracefully
            health = manager.get_health_status()

            assert health["status"] == "unhealthy"
            assert health["database_connected"] is False
            assert "error" in health

    def test_empty_database_stats(self, db_manager):
        """Test database stats with empty database."""
        stats = db_manager.get_database_stats()

        assert stats.total_monsters == 0
        assert stats.total_spells == 0
        assert stats.total_weapons == 0
        assert stats.database_size > 0  # Database file still has schema
        assert stats.connection_healthy is True

    def test_concurrent_access(self, db_manager, sample_monster):
        """Test concurrent database access."""
        import threading

        results = []
        errors = []

        def create_monster(index):
            try:
                monster = Monster(
                    monster_id=sample_monster.monster_id,
                    monster_name=f"Test Monster {index}",
                    armor_class=sample_monster.armor_class,
                    hit_points=sample_monster.hit_points,
                    strength=sample_monster.strength,
                    dexterity=sample_monster.dexterity,
                    constitution=sample_monster.constitution,
                    intelligence=sample_monster.intelligence,
                    wisdom=sample_monster.wisdom,
                    charisma=sample_monster.charisma,
                    challenge_rating=sample_monster.challenge_rating,
                    actions=sample_monster.actions,
                    special_abilities=sample_monster.special_abilities,
                    description=sample_monster.description,
                    srd_compliance=sample_monster.srd_compliance,
                    data_source=sample_monster.data_source,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_active=True,
                )
                monster_id = db_manager.create_monster(monster, f"user_{index}")
                results.append(monster_id)
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_monster, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(results) == 5  # All monsters should be created
        assert len(errors) == 0  # No errors should occur

    @patch("packages.backend.components.srd_database_manager.sqlite3.connect")
    def test_database_connection_failure(self, mock_connect, db_manager):
        """Test handling of database connection failures."""
        mock_connect.side_effect = sqlite3.Error("Connection failed")

        # Operations should handle connection errors gracefully
        health = db_manager.get_health_status()
        assert health["status"] == "unhealthy"


class TestDatabaseStats:
    """Test cases for DatabaseStats model."""

    def test_database_stats_creation(self):
        """Test DatabaseStats creation."""
        stats = DatabaseStats(
            total_monsters=10,
            total_spells=50,
            total_weapons=25,
            database_size=1024000,
            last_backup=datetime.utcnow(),
            schema_version="1.0",
            connection_healthy=True,
        )

        assert stats.total_monsters == 10
        assert stats.total_spells == 50
        assert stats.total_weapons == 25
        assert stats.database_size == 1024000
        assert stats.schema_version == "1.0"
        assert stats.connection_healthy is True

    def test_database_stats_defaults(self):
        """Test DatabaseStats default values."""
        stats = DatabaseStats()

        assert stats.total_monsters == 0
        assert stats.total_spells == 0
        assert stats.total_weapons == 0
        assert stats.database_size == 0
        assert stats.last_backup is None
        assert stats.schema_version == "1.0"
        assert stats.connection_healthy is True
