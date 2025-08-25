"""
SRD Data Import Service for D&D 5.1 System Reference Document.

This module provides data import functionality for SRD data including:
- JSON/CSV data import with validation
- Bulk data processing with error handling
- Data normalization and transformation
- Import progress tracking and reporting
- Conflict resolution strategies
"""

import csv
import hashlib
import json
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from packages.backend.components.srd_database_manager import SRDDatabaseManager
from packages.shared.logging_config import get_logger
from packages.shared.models import DataSource, Monster, Spell, SRDCompliance, Weapon

logger = get_logger(__name__)


class ImportStatus(Enum):
    """Import operation status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConflictResolution(Enum):
    """Strategy for handling data conflicts."""

    SKIP = "skip"
    UPDATE = "update"
    FAIL = "fail"
    MERGE = "merge"


@dataclass
class ImportResult:
    """Result of an import operation."""

    total_records: int = 0
    successful_imports: int = 0
    failed_imports: int = 0
    skipped_records: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    processing_time: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ImportProgress:
    """Import operation progress tracking."""

    status: ImportStatus = ImportStatus.PENDING
    current_record: int = 0
    total_records: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[ImportResult] = None


class SRDDataImportService:
    """
    Service for importing SRD data from various sources.

    Features:
    - Support for JSON and CSV file formats
    - Data validation and transformation
    - Bulk import with progress tracking
    - Conflict resolution strategies
    - Import history and rollback support
    """

    def __init__(self, database_path: Optional[str] = None):
        self.logger = get_logger(f"{__name__}.SRDDataImportService")
        self._active_imports: Dict[str, ImportProgress] = {}
        self._database_path = database_path
        self._db_manager = None

    def _get_database_manager(self) -> SRDDatabaseManager:
        """Get or create database manager instance."""
        if self._db_manager is None:
            # Create a unique database path for this service instance to avoid conflicts
            if self._database_path is None:
                unique_id = f"srd_import_{id(self)}_{hash(tempfile.mktemp())}"
                self._database_path = str(Path(tempfile.gettempdir()) / f"{unique_id}.sqlite")
            self._db_manager = SRDDatabaseManager(self._database_path)
        return self._db_manager

    def import_from_json_file(
        self,
        file_path: str,
        data_type: str,
        user: str = "system",
        conflict_resolution: ConflictResolution = ConflictResolution.UPDATE,
        batch_size: int = 100,
    ) -> ImportResult:
        """Import SRD data from a JSON file."""
        try:
            import_id = f"json_import_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            progress = ImportProgress(
                status=ImportStatus.IN_PROGRESS, start_time=datetime.utcnow()
            )
            self._active_imports[import_id] = progress

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data_type not in data:
                raise ValueError(f"Data type '{data_type}' not found in JSON file")

            records = data[data_type]
            progress.total_records = len(records)

            result = self._import_records(
                records, data_type, user, conflict_resolution, batch_size, progress
            )

            progress.status = ImportStatus.COMPLETED
            progress.end_time = datetime.utcnow()
            progress.result = result

            self.logger.info(
                "JSON import completed",
                import_id=import_id,
                data_type=data_type,
                total_records=result.total_records,
                successful_imports=result.successful_imports,
                failed_imports=result.failed_imports,
            )

            return result

        except Exception as e:
            if import_id in self._active_imports:
                self._active_imports[import_id].status = ImportStatus.FAILED
                self._active_imports[import_id].end_time = datetime.utcnow()

            self.logger.error("JSON import failed", error=str(e))
            raise

        finally:
            if import_id in self._active_imports:
                del self._active_imports[import_id]

    def import_from_csv_file(
        self,
        file_path: str,
        data_type: str,
        user: str = "system",
        conflict_resolution: ConflictResolution = ConflictResolution.UPDATE,
        batch_size: int = 100,
    ) -> ImportResult:
        """Import SRD data from a CSV file."""
        try:
            import_id = f"csv_import_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            progress = ImportProgress(
                status=ImportStatus.IN_PROGRESS, start_time=datetime.utcnow()
            )
            self._active_imports[import_id] = progress

            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                records = list(reader)

            progress.total_records = len(records)

            result = self._import_records(
                records, data_type, user, conflict_resolution, batch_size, progress
            )

            progress.status = ImportStatus.COMPLETED
            progress.end_time = datetime.utcnow()
            progress.result = result

            self.logger.info(
                "CSV import completed",
                import_id=import_id,
                data_type=data_type,
                total_records=result.total_records,
                successful_imports=result.successful_imports,
                failed_imports=result.failed_imports,
            )

            return result

        except Exception as e:
            if import_id in self._active_imports:
                self._active_imports[import_id].status = ImportStatus.FAILED
                self._active_imports[import_id].end_time = datetime.utcnow()

            self.logger.error("CSV import failed", error=str(e))
            raise

        finally:
            if import_id in self._active_imports:
                del self._active_imports[import_id]

    def _import_records(
        self,
        records: List[Dict[str, Any]],
        data_type: str,
        user: str,
        conflict_resolution: ConflictResolution,
        batch_size: int,
        progress: ImportProgress,
    ) -> ImportResult:
        """Import records in batches with progress tracking."""
        result = ImportResult(total_records=len(records))
        start_time = datetime.utcnow()

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]

            for record in batch:
                try:
                    # Transform and validate record
                    validated_record = self._validate_and_transform_record(
                        record, data_type
                    )

                    if validated_record is None:
                        result.skipped_records += 1
                        continue

                    # Create SRD entity
                    srd_entity = self._create_srd_entity(validated_record, data_type)

                    if srd_entity is None:
                        result.failed_imports += 1
                        continue

                    # Check for conflicts
                    if conflict_resolution == ConflictResolution.SKIP:
                        if self._record_exists(srd_entity, data_type):
                            result.skipped_records += 1
                            continue

                    # Import record
                    self._import_single_record(srd_entity, data_type, user)
                    result.successful_imports += 1

                except Exception as e:
                    result.failed_imports += 1
                    result.errors.append(
                        f"Record {i + result.successful_imports + result.failed_imports}: {str(e)}"
                    )

                progress.current_record = i + len(batch)

        result.processing_time = (datetime.utcnow() - start_time).total_seconds()
        return result

    def _validate_and_transform_record(
        self, record: Dict[str, Any], data_type: str
    ) -> Optional[Dict[str, Any]]:
        """Validate and transform a record for import."""
        try:
            if data_type == "monsters":
                return self._validate_monster_record(record)
            elif data_type == "spells":
                return self._validate_spell_record(record)
            elif data_type == "weapons":
                return self._validate_weapon_record(record)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")

        except Exception as e:
            self.logger.warning("Record validation failed", error=str(e))
            return None

    def _validate_monster_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and transform monster record."""
        required_fields = [
            "monster_name",
            "armor_class",
            "hit_points",
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
            "challenge_rating",
        ]

        # Check required fields
        for field in required_fields:
            if field not in record or record[field] is None:
                raise ValueError(f"Missing required field: {field}")

        # Validate ability scores
        ability_scores = [
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ]
        for score in ability_scores:
            value = record[score]
            if isinstance(value, str):
                value = int(value)
            if not (1 <= value <= 30):
                raise ValueError(f"Invalid {score} score: {value}")

        return {
            "monster_name": str(record["monster_name"]).strip(),
            "armor_class": int(record["armor_class"]),
            "hit_points": str(record["hit_points"]).strip(),
            "strength": int(record["strength"]),
            "dexterity": int(record["dexterity"]),
            "constitution": int(record["constitution"]),
            "intelligence": int(record["intelligence"]),
            "wisdom": int(record["wisdom"]),
            "charisma": int(record["charisma"]),
            "challenge_rating": str(record["challenge_rating"]).strip(),
            "actions": record.get("actions", ""),
            "special_abilities": record.get("special_abilities", ""),
            "description": record.get("description", ""),
        }

    def _validate_spell_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and transform spell record."""
        required_fields = [
            "spell_name",
            "level",
            "school",
            "casting_time",
            "range",
            "components",
            "duration",
            "description",
        ]

        # Check required fields
        for field in required_fields:
            if field not in record or record[field] is None:
                raise ValueError(f"Missing required field: {field}")

        # Validate level
        level = int(record["level"])
        if not (0 <= level <= 9):
            raise ValueError(f"Invalid spell level: {level}")

        return {
            "spell_name": str(record["spell_name"]).strip(),
            "level": level,
            "school": str(record["school"]).strip(),
            "casting_time": str(record["casting_time"]).strip(),
            "range": str(record["range"]).strip(),
            "components": str(record["components"]).strip(),
            "duration": str(record["duration"]).strip(),
            "description": str(record["description"]).strip(),
            "at_higher_levels": record.get("at_higher_levels", ""),
            "classes": record.get("classes", []),
        }

    def _validate_weapon_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and transform weapon record."""
        required_fields = [
            "weapon_name",
            "category",
            "cost",
            "damage",
            "weight",
            "properties",
        ]

        # Check required fields
        for field in required_fields:
            if field not in record or record[field] is None:
                raise ValueError(f"Missing required field: {field}")

        return {
            "weapon_name": str(record["weapon_name"]).strip(),
            "category": str(record["category"]).strip(),
            "cost": str(record["cost"]).strip(),
            "damage": str(record["damage"]).strip(),
            "weight": str(record["weight"]).strip(),
            "properties": record.get("properties", []),
            "description": record.get("description", ""),
        }

    def _create_srd_entity(
        self, record: Dict[str, Any], data_type: str
    ) -> Optional[Union[Monster, Spell, Weapon]]:
        """Create SRD entity from validated record."""
        try:
            # Create data source
            data_source = DataSource(
                source_name="SRD 5.1 Import",
                source_url="https://dnd.wizards.com/articles/features/systems-reference-document-srd",
                publication_date=datetime(2016, 5, 12),  # SRD 5.1 publication date
                version="5.1",
                checksum=self._calculate_record_hash(record),
                is_official=True,
                attribution_required=True,
            )

            # Create compliance record
            srd_compliance = SRDCompliance(
                data_source="D&D 5.1 SRD",
                license_version="5.1",
                usage_restrictions=[
                    "Must include Wizards of the Coast attribution",
                    "Cannot be used in commercial products",
                    "Must be distributed under OGL 1.0a",
                ],
                last_verified=datetime.utcnow(),
                verification_hash=self._calculate_record_hash(record),
                compliance_officer="SRD Import Service",
                audit_trail=[
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "action": "imported",
                        "user": "SRD Import Service",
                        "details": f"Record imported from {data_type} data"
                    }
                ],
            )

            if data_type == "monsters":
                return Monster(
                    monster_name=record["monster_name"],
                    armor_class=record["armor_class"],
                    hit_points=record["hit_points"],
                    strength=record["strength"],
                    dexterity=record["dexterity"],
                    constitution=record["constitution"],
                    intelligence=record["intelligence"],
                    wisdom=record["wisdom"],
                    charisma=record["charisma"],
                    challenge_rating=record["challenge_rating"],
                    actions=record["actions"],
                    special_abilities=record["special_abilities"],
                    description=record["description"],
                    srd_compliance=srd_compliance,
                    data_source=data_source,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_active=True,
                )

            elif data_type == "spells":
                return Spell(
                    spell_name=record["spell_name"],
                    level=record["level"],
                    school=record["school"],
                    casting_time=record["casting_time"],
                    range=record["range"],
                    components=record["components"],
                    duration=record["duration"],
                    description=record["description"],
                    at_higher_levels=record["at_higher_levels"],
                    classes=record["classes"],
                    srd_compliance=srd_compliance,
                    data_source=data_source,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_active=True,
                )

            elif data_type == "weapons":
                return Weapon(
                    weapon_name=record["weapon_name"],
                    category=record["category"],
                    cost=record["cost"],
                    damage=record["damage"],
                    weight=record["weight"],
                    properties=record["properties"],
                    description=record["description"],
                    srd_compliance=srd_compliance,
                    data_source=data_source,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_active=True,
                )

        except Exception as e:
            self.logger.error("Failed to create SRD entity", error=str(e))
            return None

    def _record_exists(
        self, entity: Union[Monster, Spell, Weapon], data_type: str
    ) -> bool:
        """Check if a record already exists in the database."""
        try:
            db_manager = self._get_database_manager()
            if isinstance(entity, Monster):
                # For monsters, check by name since ID might not be set for new records
                monster = db_manager.get_monster_by_name(entity.monster_name)
                return monster is not None
            elif isinstance(entity, Spell):
                # For spells, we check by name and level since ID might not be set
                return (
                    len(
                        [
                            s
                            for s in db_manager.get_spells_by_level(
                                entity.level
                            )
                            if s.spell_name == entity.spell_name
                        ]
                    )
                    > 0
                )
            elif isinstance(entity, Weapon):
                return (
                    len(
                        [
                            w
                            for w in db_manager.get_weapons_by_category(
                                entity.category
                            )
                            if w.weapon_name == entity.weapon_name
                        ]
                    )
                    > 0
                )

        except Exception as e:
            self.logger.warning("Failed to check record existence", error=str(e))

        return False

    def _import_single_record(
        self, entity: Union[Monster, Spell, Weapon], data_type: str, user: str
    ) -> None:
        """Import a single record to the database."""
        try:
            db_manager = self._get_database_manager()
            if isinstance(entity, Monster):
                db_manager.create_monster(entity, user)
            elif isinstance(entity, Spell):
                db_manager.create_spell(entity, user)
            elif isinstance(entity, Weapon):
                db_manager.create_weapon(entity, user)

        except Exception as e:
            self.logger.error("Failed to import single record", error=str(e))
            raise

    def _calculate_record_hash(self, record: Dict[str, Any]) -> str:
        """Calculate hash for record verification."""
        record_str = json.dumps(record, sort_keys=True)
        return hashlib.sha256(record_str.encode()).hexdigest()

    def get_import_progress(self, import_id: str) -> Optional[ImportProgress]:
        """Get progress of an active import operation."""
        return self._active_imports.get(import_id)

    def cancel_import(self, import_id: str) -> bool:
        """Cancel an active import operation."""
        if import_id in self._active_imports:
            self._active_imports[import_id].status = ImportStatus.CANCELLED
            self._active_imports[import_id].end_time = datetime.utcnow()
            return True
        return False

    def get_import_history(self) -> List[Dict[str, Any]]:
        """Get history of completed imports."""
        # This would typically read from a database table
        # For now, return empty list
        return []


# Global SRD data import service instance
srd_data_import_service = SRDDataImportService()
