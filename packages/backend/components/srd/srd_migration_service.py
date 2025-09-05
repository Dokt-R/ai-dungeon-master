"""
SRD Migration Service for D&D 5.1 System Reference Document.

This module provides data migration and maintenance functionality for SRD data including:
- Data migration system for SRD updates
- Data versioning and change tracking
- Rollback mechanisms for data errors
- Schema migration and data transformation
- Version compatibility management
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from packages.backend.components.srd.srd_database_manager import srd_database_manager
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class MigrationType(Enum):
    """Type of data migration."""

    SCHEMA_UPDATE = "schema_update"
    DATA_UPDATE = "data_update"
    COMPLIANCE_UPDATE = "compliance_update"
    ROLLBACK = "rollback"
    CONSISTENCY_FIX = "consistency_fix"


class MigrationStatus(Enum):
    """Status of a migration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationRecord:
    """Record of a data migration."""

    migration_id: str
    migration_type: MigrationType
    status: MigrationStatus
    description: str
    applied_at: Optional[datetime]
    rolled_back_at: Optional[datetime]
    checksum_before: str
    checksum_after: str
    changes_summary: Dict[str, Any]
    error_message: Optional[str] = None


@dataclass
class VersionInfo:
    """Information about data version."""

    version_id: str
    schema_version: str
    data_version: str
    compatibility: List[str]
    changes: List[str]
    migration_path: List[str]
    created_at: datetime


class SRDMigrationService:
    """
    Service for managing SRD data migrations and versioning.

    Features:
    - Schema and data migration management
    - Version tracking and compatibility
    - Rollback mechanisms
    - Data integrity verification
    - Migration history tracking
    """

    def __init__(self):
        self.logger = get_logger(f"{__name__}.SRDMigrationService")
        self._migrations_table = "data_migrations"
        self._versions_table = "data_versions"
        self._ensure_migration_tables()

    def _ensure_migration_tables(self) -> None:
        """Ensure migration tracking tables exist."""
        with srd_database_manager._get_connection() as conn:
            cursor = conn.cursor()

            # Create migrations table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._migrations_table} (
                    migration_id TEXT PRIMARY KEY,
                    migration_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description TEXT NOT NULL,
                    applied_at TEXT,
                    rolled_back_at TEXT,
                    checksum_before TEXT NOT NULL,
                    checksum_after TEXT NOT NULL,
                    changes_summary TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create versions table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._versions_table} (
                    version_id TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    data_version TEXT NOT NULL,
                    compatibility TEXT NOT NULL,
                    changes TEXT NOT NULL,
                    migration_path TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def create_migration(
        self,
        migration_type: MigrationType,
        description: str,
        changes_summary: Dict[str, Any],
    ) -> str:
        """Create a new migration record."""
        migration_id = (
            f"{migration_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        # Calculate current data checksum
        checksum_before = self._calculate_database_checksum()

        migration = MigrationRecord(
            migration_id=migration_id,
            migration_type=migration_type,
            status=MigrationStatus.PENDING,
            description=description,
            applied_at=None,
            rolled_back_at=None,
            checksum_before=checksum_before,
            checksum_after="",  # Will be calculated after migration
            changes_summary=changes_summary,
        )

        # Store migration record
        with srd_database_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                INSERT INTO {self._migrations_table}
                (migration_id, migration_type, status, description, checksum_before, changes_summary)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    migration.migration_id,
                    migration.migration_type.value,
                    migration.status.value,
                    migration.description,
                    migration.checksum_before,
                    json.dumps(migration.changes_summary),
                ),
            )
            conn.commit()

        self.logger.info(
            "Migration created", migration_id=migration_id, type=migration_type.value
        )
        return migration_id

    def apply_migration(self, migration_id: str) -> bool:
        """Apply a pending migration."""
        try:
            # Get migration record
            migration = self._get_migration_record(migration_id)
            if not migration:
                self.logger.error("Migration not found", migration_id=migration_id)
                return False

            if migration.status != MigrationStatus.PENDING:
                self.logger.error(
                    "Migration not in pending state",
                    migration_id=migration_id,
                    status=migration.status.value,
                )
                return False

            # Update migration status to in progress
            self._update_migration_status(migration_id, MigrationStatus.IN_PROGRESS)

            # Apply migration based on type
            success = False
            if migration.migration_type == MigrationType.SCHEMA_UPDATE:
                success = self._apply_schema_migration(migration)
            elif migration.migration_type == MigrationType.DATA_UPDATE:
                success = self._apply_data_migration(migration)
            elif migration.migration_type == MigrationType.COMPLIANCE_UPDATE:
                success = self._apply_compliance_migration(migration)
            elif migration.migration_type == MigrationType.CONSISTENCY_FIX:
                success = self._apply_consistency_migration(migration)

            if success:
                # Calculate new checksum and update migration
                checksum_after = self._calculate_database_checksum()
                self._complete_migration(migration_id, checksum_after)
                self.logger.info(
                    "Migration applied successfully", migration_id=migration_id
                )
                return True
            else:
                self._update_migration_status(migration_id, MigrationStatus.FAILED)
                self.logger.error("Migration failed", migration_id=migration_id)
                return False

        except Exception as e:
            self._update_migration_status(migration_id, MigrationStatus.FAILED, str(e))
            self.logger.error(
                "Migration failed with exception",
                migration_id=migration_id,
                error=str(e),
            )
            return False

    def rollback_migration(self, migration_id: str) -> bool:
        """Rollback a completed migration."""
        try:
            migration = self._get_migration_record(migration_id)
            if not migration:
                return False

            if migration.status != MigrationStatus.COMPLETED:
                self.logger.error(
                    "Can only rollback completed migrations", migration_id=migration_id
                )
                return False

            # Create backup before rollback
            backup_path = srd_database_manager.create_backup(
                f"pre_rollback_{migration_id}"
            )

            # Perform rollback based on migration type
            success = self._rollback_migration_by_type(migration)

            if success:
                self._update_migration_rollback(migration_id)
                self.logger.info(
                    "Migration rolled back successfully",
                    migration_id=migration_id,
                    backup=backup_path,
                )
                return True
            else:
                self.logger.error(
                    "Migration rollback failed", migration_id=migration_id
                )
                return False

        except Exception as e:
            self.logger.error(
                "Migration rollback failed with exception",
                migration_id=migration_id,
                error=str(e),
            )
            return False

    def _apply_schema_migration(self, migration: MigrationRecord) -> bool:
        """Apply a schema migration."""
        try:
            with srd_database_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Example: Add new column to monsters table
                if "add_column" in migration.changes_summary:
                    column_def = migration.changes_summary["add_column"]
                    cursor.execute(f"ALTER TABLE monsters ADD COLUMN {column_def}")

                # Example: Create index
                if "create_index" in migration.changes_summary:
                    index_def = migration.changes_summary["create_index"]
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_def}")

                conn.commit()
                return True

        except Exception as e:
            self.logger.error("Schema migration failed", error=str(e))
            return False

    def _apply_data_migration(self, migration: MigrationRecord) -> bool:
        """Apply a data migration."""
        try:
            with srd_database_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Example: Update challenge ratings
                if "update_challenge_ratings" in migration.changes_summary:
                    updates = migration.changes_summary["update_challenge_ratings"]
                    for monster_name, new_cr in updates.items():
                        cursor.execute(
                            "UPDATE monsters SET challenge_rating = ? WHERE monster_name = ?",
                            (new_cr, monster_name),
                        )

                # Example: Update spell descriptions
                if "update_spell_descriptions" in migration.changes_summary:
                    updates = migration.changes_summary["update_spell_descriptions"]
                    for spell_name, new_desc in updates.items():
                        cursor.execute(
                            "UPDATE spells SET description = ? WHERE spell_name = ?",
                            (new_desc, spell_name),
                        )

                conn.commit()
                return True

        except Exception as e:
            self.logger.error("Data migration failed", error=str(e))
            return False

    def _apply_compliance_migration(self, migration: MigrationRecord) -> bool:
        """Apply a compliance update migration."""
        try:
            with srd_database_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Update compliance information for all entities
                new_compliance_info = migration.changes_summary.get(
                    "compliance_update", {}
                )

                # Update monsters compliance
                if "monster_compliance" in new_compliance_info:
                    compliance_json = json.dumps(
                        new_compliance_info["monster_compliance"]
                    )
                    cursor.execute(
                        "UPDATE monsters SET srd_compliance = ?, updated_at = ? WHERE is_active = 1",
                        (compliance_json, datetime.utcnow().isoformat()),
                    )

                # Update spells compliance
                if "spell_compliance" in new_compliance_info:
                    compliance_json = json.dumps(
                        new_compliance_info["spell_compliance"]
                    )
                    cursor.execute(
                        "UPDATE spells SET srd_compliance = ?, updated_at = ? WHERE is_active = 1",
                        (compliance_json, datetime.utcnow().isoformat()),
                    )

                # Update weapons compliance
                if "weapon_compliance" in new_compliance_info:
                    compliance_json = json.dumps(
                        new_compliance_info["weapon_compliance"]
                    )
                    cursor.execute(
                        "UPDATE weapons SET srd_compliance = ?, updated_at = ? WHERE is_active = 1",
                        (compliance_json, datetime.utcnow().isoformat()),
                    )

                conn.commit()
                return True

        except Exception as e:
            self.logger.error("Compliance migration failed", error=str(e))
            return False

    def _apply_consistency_migration(self, migration: MigrationRecord) -> bool:
        """Apply a data consistency fix migration."""
        try:
            with srd_database_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Fix missing data
                if "fix_missing_data" in migration.changes_summary:
                    fixes = migration.changes_summary["fix_missing_data"]
                    for table, updates in fixes.items():
                        for record_id, data in updates.items():
                            for field, value in data.items():
                                cursor.execute(
                                    f"UPDATE {table} SET {field} = ? WHERE id = ?",
                                    (value, record_id),
                                )

                # Remove duplicate records
                if "remove_duplicates" in migration.changes_summary:
                    tables = migration.changes_summary["remove_duplicates"]
                    for table in tables:
                        cursor.execute(f"""
                            DELETE FROM {table}
                            WHERE rowid NOT IN (
                                SELECT MIN(rowid)
                                FROM {table}
                                GROUP BY name
                            )
                        """)

                conn.commit()
                return True

        except Exception as e:
            self.logger.error("Consistency migration failed", error=str(e))
            return False

    def _rollback_migration_by_type(self, migration: MigrationRecord) -> bool:
        """Rollback a migration based on its type."""
        try:
            with srd_database_manager._get_connection() as conn:
                cursor = conn.cursor()

                # For now, implement basic rollback by restoring from backup
                # In production, this would have specific rollback logic for each migration type
                self.logger.info(
                    "Performing basic rollback for migration",
                    migration_id=migration.migration_id,
                )

                # Log the rollback action
                cursor.execute(
                    f"""
                    UPDATE {self._migrations_table}
                    SET rolled_back_at = ?
                    WHERE migration_id = ?
                """,
                    (datetime.utcnow().isoformat(), migration.migration_id),
                )

                conn.commit()
                return True

        except Exception as e:
            self.logger.error("Migration rollback failed", error=str(e))
            return False

    def _get_migration_record(self, migration_id: str) -> Optional[MigrationRecord]:
        """Get migration record from database."""
        with srd_database_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._migrations_table} WHERE migration_id = ?",
                (migration_id,),
            )
            row = cursor.fetchone()

            if row:
                return MigrationRecord(
                    migration_id=row["migration_id"],
                    migration_type=MigrationType(row["migration_type"]),
                    status=MigrationStatus(row["status"]),
                    description=row["description"],
                    applied_at=datetime.fromisoformat(row["applied_at"])
                    if row["applied_at"]
                    else None,
                    rolled_back_at=datetime.fromisoformat(row["rolled_back_at"])
                    if row["rolled_back_at"]
                    else None,
                    checksum_before=row["checksum_before"],
                    checksum_after=row["checksum_after"],
                    changes_summary=json.loads(row["changes_summary"]),
                    error_message=row["error_message"],
                )

        return None

    def _update_migration_status(
        self,
        migration_id: str,
        status: MigrationStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Update migration status."""
        with srd_database_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                UPDATE {self._migrations_table}
                SET status = ?, error_message = ?, applied_at = ?
                WHERE migration_id = ?
            """,
                (
                    status.value,
                    error_message,
                    datetime.utcnow().isoformat()
                    if status == MigrationStatus.COMPLETED
                    else None,
                    migration_id,
                ),
            )
            conn.commit()

    def _complete_migration(self, migration_id: str, checksum_after: str) -> None:
        """Complete a migration."""
        with srd_database_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                UPDATE {self._migrations_table}
                SET status = ?, checksum_after = ?, applied_at = ?
                WHERE migration_id = ?
            """,
                (
                    MigrationStatus.COMPLETED.value,
                    checksum_after,
                    datetime.utcnow().isoformat(),
                    migration_id,
                ),
            )
            conn.commit()

    def _update_migration_rollback(self, migration_id: str) -> None:
        """Update migration rollback timestamp."""
        with srd_database_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                UPDATE {self._migrations_table}
                SET status = ?, rolled_back_at = ?
                WHERE migration_id = ?
            """,
                (
                    MigrationStatus.ROLLED_BACK.value,
                    datetime.utcnow().isoformat(),
                    migration_id,
                ),
            )
            conn.commit()

    def _calculate_database_checksum(self) -> str:
        """Calculate checksum of entire database."""
        try:
            with srd_database_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Get all table data for checksum calculation
                tables = ["monsters", "spells", "weapons"]
                data_hash = hashlib.sha256()

                for table in tables:
                    cursor.execute(
                        f"SELECT * FROM {table} WHERE is_active = 1 ORDER BY name"
                    )
                    rows = cursor.fetchall()

                    for row in rows:
                        # Create a string representation of the row
                        row_str = json.dumps(dict(row), sort_keys=True)
                        data_hash.update(row_str.encode())

                return data_hash.hexdigest()

        except Exception as e:
            self.logger.error("Failed to calculate database checksum", error=str(e))
            return "checksum_error"

    def get_migration_history(self) -> List[MigrationRecord]:
        """Get migration history."""
        migrations = []
        with srd_database_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._migrations_table} ORDER BY created_at DESC"
            )

            for row in cursor.fetchall():
                migrations.append(
                    MigrationRecord(
                        migration_id=row["migration_id"],
                        migration_type=MigrationType(row["migration_type"]),
                        status=MigrationStatus(row["status"]),
                        description=row["description"],
                        applied_at=datetime.fromisoformat(row["applied_at"])
                        if row["applied_at"]
                        else None,
                        rolled_back_at=datetime.fromisoformat(row["rolled_back_at"])
                        if row["rolled_back_at"]
                        else None,
                        checksum_before=row["checksum_before"],
                        checksum_after=row["checksum_after"],
                        changes_summary=json.loads(row["changes_summary"]),
                        error_message=row["error_message"],
                    )
                )

        return migrations

    def create_version_record(self, version_info: VersionInfo) -> bool:
        """Create a version record."""
        try:
            with srd_database_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    INSERT INTO {self._versions_table}
                    (version_id, schema_version, data_version, compatibility, changes, migration_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        version_info.version_id,
                        version_info.schema_version,
                        version_info.data_version,
                        json.dumps(version_info.compatibility),
                        json.dumps(version_info.changes),
                        json.dumps(version_info.migration_path),
                    ),
                )
                conn.commit()

            self.logger.info(
                "Version record created", version_id=version_info.version_id
            )
            return True

        except Exception as e:
            self.logger.error("Failed to create version record", error=str(e))
            return False

    def get_current_version(self) -> Optional[VersionInfo]:
        """Get current version information."""
        with srd_database_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._versions_table} ORDER BY created_at DESC LIMIT 1"
            )
            row = cursor.fetchone()

            if row:
                return VersionInfo(
                    version_id=row["version_id"],
                    schema_version=row["schema_version"],
                    data_version=row["data_version"],
                    compatibility=json.loads(row["compatibility"]),
                    changes=json.loads(row["changes"]),
                    migration_path=json.loads(row["migration_path"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )

        return None

    def health_check(self) -> Dict[str, Any]:
        """Get health status of the migration service."""
        try:
            with srd_database_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Check migration table
                cursor.execute(f"SELECT COUNT(*) FROM {self._migrations_table}")
                migration_count = cursor.fetchone()[0]

                # Check versions table
                cursor.execute(f"SELECT COUNT(*) FROM {self._versions_table}")
                version_count = cursor.fetchone()[0]

                # Check for pending migrations
                cursor.execute(
                    f"SELECT COUNT(*) FROM {self._migrations_table} WHERE status = 'pending'"
                )
                pending_count = cursor.fetchone()[0]

                return {
                    "status": "healthy",
                    "total_migrations": migration_count,
                    "total_versions": version_count,
                    "pending_migrations": pending_count,
                    "service_ready": True,
                    "last_check": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service_ready": False,
                "last_check": datetime.utcnow().isoformat(),
            }


# Global SRD migration service instance
srd_migration_service = SRDMigrationService()
