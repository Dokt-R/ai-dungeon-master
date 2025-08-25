"""
SRD Database Manager for D&D 5.1 System Reference Document.

This module provides database management functionality for SRD data including:
- SQLite database schema management and migrations
- Data import/export with validation
- Backup and recovery procedures
- Query optimization and indexing
- CRUD operations for monsters, spells, and weapons

FUTURE: Consider migrating to SQLModel/SQLAlchemy like CampaignManager for consistency.
Current SQLite approach prioritizes:
- Simplicity for isolated SRD operations
- No async complexity for file-based operations
- Direct control over schema evolution
- Independence from main application database

🏗️ Recommended Migration Strategy
If you want to align the SRD system with the SQLModel pattern, here's how I'd approach it:

Phase 1: Create SRD SQLModel Classes
# packages/shared/models.py - Add SRD SQLModels
class SRDMonster(SQLModel, table=True):
    __tablename__ = "srd_monsters"
    monster_id: Optional[int] = SQLField(primary_key=True)
    monster_name: str = SQLField(unique=True)
    # ... other fields

class SRDSpell(SQLModel, table=True):
    __tablename__ = "srd_spells"
    spell_id: Optional[int] = SQLField(primary_key=True)
    spell_name: str = SQLField(unique=True)
    # ... other fields

python


Phase 2: Update SRD Database Manager
class SRDDatabaseManager:
    def __init__(self, session: AsyncSession = Depends(get_async_session)):
        self.session = session

    async def create_monster(self, monster: Monster) -> int:
        srd_monster = SRDMonster(**monster.model_dump())
        self.session.add(srd_monster)
        await self.session.commit()
        return srd_monster.monster_id

python


Phase 3: Migration Benefits
Consistency: All database operations follow the same pattern
Better testing: Can use the same test fixtures as campaign manager
Async support: Better performance for concurrent operations
Built-in validation: Pydantic integration through SQLModel
🎯 Current Recommendation
For the immediate term, the SQLite approach is acceptable because:

SRD data is relatively static - it's reference data, not transactional data
File-based distribution - easy to share/pack with the application
Performance - direct SQLite queries are very fast for read-heavy operations
Isolation - keeps SRD concerns separate from main application logic
"""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from packages.backend.components.srd_compliance_service import srd_compliance_service
from packages.shared.logging_config import get_logger
from packages.shared.models import DataSource, Monster, Spell, SRDCompliance, Weapon

logger = get_logger(__name__)


@dataclass
class DatabaseStats:
    """Database statistics and health information."""

    total_monsters: int = 0
    total_spells: int = 0
    total_weapons: int = 0
    database_size: int = 0
    last_backup: Optional[datetime] = None
    schema_version: str = "1.0"
    connection_healthy: bool = True


class SRDDatabaseManager:
    """
    Database manager for SRD data with compliance tracking.

    Features:
    - Database schema management and migrations
    - CRUD operations for all SRD entities
    - Data import/export with validation
    - Backup and recovery procedures
    - Query optimization and indexing
    - Compliance integration
    """

    def __init__(self, database_path: Optional[str] = None):
        self.logger = get_logger(f"{__name__}.SRDDatabaseManager")

        # Database path
        self.database_path = database_path or "data/srd_database.sqlite"
        self._ensure_database_exists()

        # Connection pool management
        self._connection_pool = {}

    def _ensure_database_exists(self) -> None:
        """Ensure the SRD database exists with proper schema."""
        db_path = Path(self.database_path)

        # Validate path is accessible before attempting to create
        try:
            # Check if we can at least resolve the path
            db_path.resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Invalid database path: {e}")

        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot create database directory: {e}")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Create monsters table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS monsters (
                        monster_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        monster_name TEXT NOT NULL UNIQUE,
                        armor_class INTEGER NOT NULL,
                        hit_points TEXT NOT NULL,
                        strength INTEGER NOT NULL,
                        dexterity INTEGER NOT NULL,
                        constitution INTEGER NOT NULL,
                        intelligence INTEGER NOT NULL,
                        wisdom INTEGER NOT NULL,
                        charisma INTEGER NOT NULL,
                        challenge_rating TEXT NOT NULL,
                        actions TEXT,
                        special_abilities TEXT,
                        description TEXT,
                        srd_compliance TEXT NOT NULL,
                        data_source TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN NOT NULL DEFAULT 1
                    )
                """)

                # Create spells table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS spells (
                        spell_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        spell_name TEXT NOT NULL UNIQUE,
                        level INTEGER NOT NULL CHECK(level >= 0 AND level <= 9),
                        school TEXT NOT NULL,
                        casting_time TEXT NOT NULL,
                        range TEXT NOT NULL,
                        components TEXT NOT NULL,
                        duration TEXT NOT NULL,
                        description TEXT NOT NULL,
                        at_higher_levels TEXT,
                        classes TEXT NOT NULL,
                        srd_compliance TEXT NOT NULL,
                        data_source TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN NOT NULL DEFAULT 1
                    )
                """)

                # Create weapons table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS weapons (
                        weapon_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        weapon_name TEXT NOT NULL UNIQUE,
                        category TEXT NOT NULL,
                        cost TEXT NOT NULL,
                        damage TEXT NOT NULL,
                        weight TEXT NOT NULL,
                        properties TEXT NOT NULL,
                        description TEXT,
                        srd_compliance TEXT NOT NULL,
                        data_source TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN NOT NULL DEFAULT 1
                    )
                """)

                # Create indexes for better query performance
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_monsters_name ON monsters(monster_name)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_monsters_cr ON monsters(challenge_rating)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spells_name ON spells(spell_name)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spells_level ON spells(level)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_weapons_name ON weapons(weapon_name)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_weapons_category ON weapons(category)"
                )

                # Create database metadata table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS database_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Set initial schema version
                cursor.execute("""
                    INSERT OR REPLACE INTO database_metadata (key, value)
                    VALUES ('schema_version', '1.0')
                """)

                conn.commit()

        except Exception as e:
            raise ValueError(f"Cannot connect to database: {e}")

        self.logger.info("SRD database initialized", database_path=self.database_path)

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

    def _serialize_compliance(self, compliance: SRDCompliance) -> str:
        """Serialize SRDCompliance to JSON string."""
        return json.dumps(
            {
                "data_source": compliance.data_source,
                "license_version": compliance.license_version,
                "usage_restrictions": compliance.usage_restrictions,
                "last_verified": compliance.last_verified.isoformat(),
                "verification_hash": compliance.verification_hash,
                "compliance_officer": compliance.compliance_officer,
                "audit_trail": compliance.audit_trail,
            }
        )

    def _deserialize_compliance(self, data: str) -> SRDCompliance:
        """Deserialize JSON string to SRDCompliance."""
        parsed = json.loads(data)
        return SRDCompliance(
            data_source=parsed["data_source"],
            license_version=parsed["license_version"],
            usage_restrictions=parsed["usage_restrictions"],
            last_verified=datetime.fromisoformat(parsed["last_verified"]),
            verification_hash=parsed["verification_hash"],
            compliance_officer=parsed.get("compliance_officer"),
            audit_trail=parsed.get("audit_trail", []),
        )

    def _serialize_data_source(self, data_source: DataSource) -> str:
        """Serialize DataSource to JSON string."""
        return json.dumps(
            {
                "source_name": data_source.source_name,
                "source_url": data_source.source_url,
                "publication_date": data_source.publication_date.isoformat(),
                "version": data_source.version,
                "checksum": data_source.checksum,
                "is_official": data_source.is_official,
                "attribution_required": data_source.attribution_required,
            }
        )

    def _validate_ability_scores(self, monster: Monster) -> None:
        """Validate monster ability scores."""
        ability_scores = [
            ("strength", monster.strength),
            ("dexterity", monster.dexterity),
            ("constitution", monster.constitution),
            ("intelligence", monster.intelligence),
            ("wisdom", monster.wisdom),
            ("charisma", monster.charisma),
        ]

        for score_name, score_value in ability_scores:
            if not (1 <= score_value <= 30):
                raise ValueError(
                    f"Invalid {score_name} score: {score_value} (must be between 1 and 30)"
                )

    def _deserialize_data_source(self, data: str) -> DataSource:
        """Deserialize JSON string to DataSource."""
        parsed = json.loads(data)
        return DataSource(
            source_name=parsed["source_name"],
            source_url=parsed["source_url"],
            publication_date=datetime.fromisoformat(parsed["publication_date"]),
            version=parsed["version"],
            checksum=parsed["checksum"],
            is_official=parsed["is_official"],
            attribution_required=parsed["attribution_required"],
        )

    # Monster CRUD Operations
    def create_monster(self, monster: Monster, user: str = "system") -> int:
        """Create a new monster in the database."""
        # Validate ability scores
        self._validate_ability_scores(monster)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO monsters (
                        monster_name, armor_class, hit_points, strength, dexterity,
                        constitution, intelligence, wisdom, charisma, challenge_rating,
                        actions, special_abilities, description, srd_compliance,
                        data_source, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        monster.monster_name,
                        monster.armor_class,
                        monster.hit_points,
                        monster.strength,
                        monster.dexterity,
                        monster.constitution,
                        monster.intelligence,
                        monster.wisdom,
                        monster.charisma,
                        monster.challenge_rating,
                        monster.actions,
                        monster.special_abilities,
                        monster.description,
                        self._serialize_compliance(monster.srd_compliance),
                        self._serialize_data_source(monster.data_source),
                        monster.created_at.isoformat(),
                        monster.updated_at.isoformat(),
                    ),
                )

                monster_id = cursor.lastrowid
                conn.commit()

                # Verify compliance
                srd_compliance_service.verify_data_compliance(monster, "monster", user)

                self.logger.info(
                    "Monster created",
                    monster_id=monster_id,
                    monster_name=monster.monster_name,
                    user=user,
                )

                return monster_id

        except Exception as e:
            self.logger.error("Failed to create monster", error=str(e))
            raise

    def get_monster(self, monster_id: int) -> Optional[Monster]:
        """Get monster by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM monsters WHERE monster_id = ? AND is_active = 1",
                    (monster_id,),
                )
                row = cursor.fetchone()

                if row:
                    return Monster(
                        monster_id=row["monster_id"],
                        monster_name=row["monster_name"],
                        armor_class=row["armor_class"],
                        hit_points=row["hit_points"],
                        strength=row["strength"],
                        dexterity=row["dexterity"],
                        constitution=row["constitution"],
                        intelligence=row["intelligence"],
                        wisdom=row["wisdom"],
                        charisma=row["charisma"],
                        challenge_rating=row["challenge_rating"],
                        actions=row["actions"],
                        special_abilities=row["special_abilities"],
                        description=row["description"],
                        srd_compliance=self._deserialize_compliance(
                            row["srd_compliance"]
                        ),
                        data_source=self._deserialize_data_source(row["data_source"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        is_active=row["is_active"],
                    )

        except Exception as e:
            self.logger.error(
                "Failed to get monster", monster_id=monster_id, error=str(e)
            )

        return None

    def get_monsters_by_challenge_rating(
        self, min_cr: float, max_cr: float
    ) -> List[Monster]:
        """Get monsters within challenge rating range."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM monsters
                    WHERE CAST(challenge_rating AS FLOAT) BETWEEN ? AND ?
                    AND is_active = 1
                    ORDER BY CAST(challenge_rating AS FLOAT)
                """,
                    (min_cr, max_cr),
                )

                monsters = []
                for row in cursor.fetchall():
                    monsters.append(
                        Monster(
                            monster_id=row["monster_id"],
                            monster_name=row["monster_name"],
                            armor_class=row["armor_class"],
                            hit_points=row["hit_points"],
                            strength=row["strength"],
                            dexterity=row["dexterity"],
                            constitution=row["constitution"],
                            intelligence=row["intelligence"],
                            wisdom=row["wisdom"],
                            charisma=row["charisma"],
                            challenge_rating=row["challenge_rating"],
                            actions=row["actions"],
                            special_abilities=row["special_abilities"],
                            description=row["description"],
                            srd_compliance=self._deserialize_compliance(
                                row["srd_compliance"]
                            ),
                            data_source=self._deserialize_data_source(
                                row["data_source"]
                            ),
                            created_at=datetime.fromisoformat(row["created_at"]),
                            updated_at=datetime.fromisoformat(row["updated_at"]),
                            is_active=row["is_active"],
                        )
                    )

                return monsters

        except Exception as e:
            self.logger.error("Failed to get monsters by CR", error=str(e))
            return []

    # Spell CRUD Operations
    def create_spell(self, spell: Spell, user: str = "system") -> int:
        """Create a new spell in the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO spells (
                        spell_name, level, school, casting_time, range, components,
                        duration, description, at_higher_levels, classes,
                        srd_compliance, data_source, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        spell.spell_name,
                        spell.level,
                        spell.school,
                        spell.casting_time,
                        spell.range,
                        spell.components,
                        spell.duration,
                        spell.description,
                        spell.at_higher_levels,
                        json.dumps(spell.classes),
                        self._serialize_compliance(spell.srd_compliance),
                        self._serialize_data_source(spell.data_source),
                        spell.created_at.isoformat(),
                        spell.updated_at.isoformat(),
                    ),
                )

                spell_id = cursor.lastrowid
                conn.commit()

                # Verify compliance
                srd_compliance_service.verify_data_compliance(spell, "spell", user)

                self.logger.info(
                    "Spell created",
                    spell_id=spell_id,
                    spell_name=spell.spell_name,
                    level=spell.level,
                    user=user,
                )

                return spell_id

        except Exception as e:
            self.logger.error("Failed to create spell", error=str(e))
            raise

    def get_spells_by_level(self, level: int) -> List[Spell]:
        """Get spells by level."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM spells
                    WHERE level = ? AND is_active = 1
                    ORDER BY spell_name
                """,
                    (level,),
                )

                spells = []
                for row in cursor.fetchall():
                    spells.append(
                        Spell(
                            spell_id=row["spell_id"],
                            spell_name=row["spell_name"],
                            level=row["level"],
                            school=row["school"],
                            casting_time=row["casting_time"],
                            range=row["range"],
                            components=row["components"],
                            duration=row["duration"],
                            description=row["description"],
                            at_higher_levels=row["at_higher_levels"],
                            classes=json.loads(row["classes"]),
                            srd_compliance=self._deserialize_compliance(
                                row["srd_compliance"]
                            ),
                            data_source=self._deserialize_data_source(
                                row["data_source"]
                            ),
                            created_at=datetime.fromisoformat(row["created_at"]),
                            updated_at=datetime.fromisoformat(row["updated_at"]),
                            is_active=row["is_active"],
                        )
                    )

                return spells

        except Exception as e:
            self.logger.error(
                "Failed to get spells by level", level=level, error=str(e)
            )
            return []

    # Weapon CRUD Operations
    def create_weapon(self, weapon: Weapon, user: str = "system") -> int:
        """Create a new weapon in the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO weapons (
                        weapon_name, category, cost, damage, weight, properties,
                        description, srd_compliance, data_source, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        weapon.weapon_name,
                        weapon.category,
                        weapon.cost,
                        weapon.damage,
                        weapon.weight,
                        json.dumps(weapon.properties),
                        weapon.description,
                        self._serialize_compliance(weapon.srd_compliance),
                        self._serialize_data_source(weapon.data_source),
                        weapon.created_at.isoformat(),
                        weapon.updated_at.isoformat(),
                    ),
                )

                weapon_id = cursor.lastrowid
                conn.commit()

                # Verify compliance
                srd_compliance_service.verify_data_compliance(weapon, "weapon", user)

                self.logger.info(
                    "Weapon created",
                    weapon_id=weapon_id,
                    weapon_name=weapon.weapon_name,
                    user=user,
                )

                return weapon_id

        except Exception as e:
            self.logger.error("Failed to create weapon", error=str(e))
            raise

    def get_weapons_by_category(self, category: str) -> List[Weapon]:
        """Get weapons by category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM weapons
                    WHERE category = ? AND is_active = 1
                    ORDER BY weapon_name
                """,
                    (category,),
                )

                weapons = []
                for row in cursor.fetchall():
                    weapons.append(
                        Weapon(
                            weapon_id=row["weapon_id"],
                            weapon_name=row["weapon_name"],
                            category=row["category"],
                            cost=row["cost"],
                            damage=row["damage"],
                            weight=row["weight"],
                            properties=json.loads(row["properties"]),
                            description=row["description"],
                            srd_compliance=self._deserialize_compliance(
                                row["srd_compliance"]
                            ),
                            data_source=self._deserialize_data_source(
                                row["data_source"]
                            ),
                            created_at=datetime.fromisoformat(row["created_at"]),
                            updated_at=datetime.fromisoformat(row["updated_at"]),
                            is_active=row["is_active"],
                        )
                    )

                return weapons

        except Exception as e:
            self.logger.error(
                "Failed to get weapons by category", category=category, error=str(e)
            )
            return []

    def get_monster_by_name(self, monster_name: str) -> Optional[Monster]:
        """Get monster by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM monsters WHERE monster_name = ? AND is_active = 1",
                    (monster_name,),
                )
                row = cursor.fetchone()

                if row:
                    return Monster(
                        monster_id=row["monster_id"],
                        monster_name=row["monster_name"],
                        armor_class=row["armor_class"],
                        hit_points=row["hit_points"],
                        strength=row["strength"],
                        dexterity=row["dexterity"],
                        constitution=row["constitution"],
                        intelligence=row["intelligence"],
                        wisdom=row["wisdom"],
                        charisma=row["charisma"],
                        challenge_rating=row["challenge_rating"],
                        actions=row["actions"],
                        special_abilities=row["special_abilities"],
                        description=row["description"],
                        srd_compliance=self._deserialize_compliance(
                            row["srd_compliance"]
                        ),
                        data_source=self._deserialize_data_source(row["data_source"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        is_active=row["is_active"],
                    )

        except Exception as e:
            self.logger.error(
                "Failed to get monster by name", monster_name=monster_name, error=str(e)
            )

        return None

    def get_spell_by_name(self, spell_name: str) -> Optional[Spell]:
        """Get spell by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM spells WHERE spell_name = ? AND is_active = 1",
                    (spell_name,),
                )
                row = cursor.fetchone()

                if row:
                    return Spell(
                        spell_id=row["spell_id"],
                        spell_name=row["spell_name"],
                        level=row["level"],
                        school=row["school"],
                        casting_time=row["casting_time"],
                        range=row["range"],
                        components=row["components"],
                        duration=row["duration"],
                        description=row["description"],
                        at_higher_levels=row["at_higher_levels"],
                        classes=json.loads(row["classes"]),
                        srd_compliance=self._deserialize_compliance(
                            row["srd_compliance"]
                        ),
                        data_source=self._deserialize_data_source(row["data_source"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        is_active=row["is_active"],
                    )

        except Exception as e:
            self.logger.error(
                "Failed to get spell by name", spell_name=spell_name, error=str(e)
            )

        return None

    def get_monster_by_name(self, monster_name: str) -> Optional[Monster]:
        """Get monster by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM monsters WHERE monster_name = ? AND is_active = 1",
                    (monster_name,),
                )
                row = cursor.fetchone()

                if row:
                    return Monster(
                        monster_id=row["monster_id"],
                        monster_name=row["monster_name"],
                        armor_class=row["armor_class"],
                        hit_points=row["hit_points"],
                        strength=row["strength"],
                        dexterity=row["dexterity"],
                        constitution=row["constitution"],
                        intelligence=row["intelligence"],
                        wisdom=row["wisdom"],
                        charisma=row["charisma"],
                        challenge_rating=row["challenge_rating"],
                        actions=row["actions"],
                        special_abilities=row["special_abilities"],
                        description=row["description"],
                        srd_compliance=self._deserialize_compliance(
                            row["srd_compliance"]
                        ),
                        data_source=self._deserialize_data_source(row["data_source"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        is_active=row["is_active"],
                    )

        except Exception as e:
            self.logger.error(
                "Failed to get monster by name", monster_name=monster_name, error=str(e)
            )

        return None

    def get_weapon_by_name(self, weapon_name: str) -> Optional[Weapon]:
        """Get weapon by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM weapons WHERE weapon_name = ? AND is_active = 1",
                    (weapon_name,),
                )
                row = cursor.fetchone()

                if row:
                    return Weapon(
                        weapon_id=row["weapon_id"],
                        weapon_name=row["weapon_name"],
                        category=row["category"],
                        cost=row["cost"],
                        damage=row["damage"],
                        weight=row["weight"],
                        properties=json.loads(row["properties"]),
                        description=row["description"],
                        srd_compliance=self._deserialize_compliance(
                            row["srd_compliance"]
                        ),
                        data_source=self._deserialize_data_source(row["data_source"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        is_active=row["is_active"],
                    )

        except Exception as e:
            self.logger.error(
                "Failed to get weapon by name", weapon_name=weapon_name, error=str(e)
            )

        return None

    # Database Management Operations
    def create_backup(self, backup_path: Optional[str] = None) -> str:
        """Create database backup."""
        try:
            if not backup_path:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.database_path}.backup_{timestamp}"

            # SQLite backup using shell command (in production, use proper backup methods)
            import shutil

            shutil.copy2(self.database_path, backup_path)

            # Update metadata
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO database_metadata (key, value)
                    VALUES ('last_backup', ?)
                """,
                    (datetime.utcnow().isoformat(),),
                )
                conn.commit()

            self.logger.info("Database backup created", backup_path=backup_path)
            return backup_path

        except Exception as e:
            self.logger.error("Failed to create backup", error=str(e))
            raise

    def get_database_stats(self) -> DatabaseStats:
        """Get database statistics and health information."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get counts
                cursor.execute("SELECT COUNT(*) FROM monsters WHERE is_active = 1")
                total_monsters = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM spells WHERE is_active = 1")
                total_spells = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM weapons WHERE is_active = 1")
                total_weapons = cursor.fetchone()[0]

                # Get database size
                db_path = Path(self.database_path)
                database_size = db_path.stat().st_size if db_path.exists() else 0

                # Get last backup
                cursor.execute(
                    "SELECT value FROM database_metadata WHERE key = 'last_backup'"
                )
                row = cursor.fetchone()
                last_backup = datetime.fromisoformat(row[0]) if row and row[0] else None

                # Get schema version
                cursor.execute(
                    "SELECT value FROM database_metadata WHERE key = 'schema_version'"
                )
                row = cursor.fetchone()
                schema_version = row[0] if row and row[0] else "1.0"

                return DatabaseStats(
                    total_monsters=total_monsters,
                    total_spells=total_spells,
                    total_weapons=total_weapons,
                    database_size=database_size,
                    last_backup=last_backup,
                    schema_version=schema_version,
                    connection_healthy=True,
                )

        except Exception as e:
            self.logger.error("Failed to get database stats", error=str(e))
            return DatabaseStats(connection_healthy=False)

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the SRD database manager."""
        try:
            stats = self.get_database_stats()

            result = {
                "status": "healthy" if stats.connection_healthy else "unhealthy",
                "database_exists": Path(self.database_path).exists(),
                "database_path": self.database_path,
                "total_monsters": stats.total_monsters,
                "total_spells": stats.total_spells,
                "total_weapons": stats.total_weapons,
                "database_size_mb": round(stats.database_size / (1024 * 1024), 2),
                "last_backup": stats.last_backup.isoformat()
                if stats.last_backup
                else None,
                "schema_version": stats.schema_version,
                "database_connected": stats.connection_healthy,
            }

            # Include error information if connection is unhealthy
            if not stats.connection_healthy:
                result["error"] = "Database connection failed"

            return result

        except Exception as e:
            return {
                "status": "unhealthy",
                "database_exists": Path(self.database_path).exists(),
                "database_path": self.database_path,
                "error": str(e),
                "database_connected": False,
            }


# Global SRD database manager instance
srd_database_manager = SRDDatabaseManager()
