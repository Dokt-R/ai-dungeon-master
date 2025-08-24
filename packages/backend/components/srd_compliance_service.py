"""
SRD Compliance Service for D&D 5.1 System Reference Document.

This module provides comprehensive compliance management for D&D SRD data usage,
including licensing verification, data source validation, audit trails, and
compliance reporting to ensure legal and ethical use of SRD content.

Key Features:
- Licensing compliance verification and tracking
- Data source validation and integrity checking
- Audit trail generation and compliance reporting
- Data update and migration management
- Usage logging for compliance monitoring
- Compliance testing and validation frameworks
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from packages.shared.logging_config import get_logger
from packages.shared.models import DataSource
from enum import Enum

logger = get_logger(__name__)


class LicenseRestriction(Enum):
    """SRD license restriction types."""

    ATTRIBUTION_REQUIRED = "attribution_required"
    NO_COMMERCIAL_USE = "no_commercial_use"
    OGL_COMPLIANCE = "ogl_compliance"


@dataclass
class ComplianceCheckResult:
    """Result of a compliance check operation."""

    is_compliant: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    check_type: str = "general"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEntry:
    """Single audit trail entry."""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    action: str = ""
    entity_type: str = ""  # monster, spell, weapon
    entity_id: Optional[int] = None
    entity_name: str = ""
    user: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    compliance_status: str = "unknown"


class SRDComplianceService:
    """
    Service for managing D&D SRD compliance and data integrity.

    Features:
    - Licensing compliance verification
    - Data source validation
    - Audit trail management
    - Compliance reporting
    - Data integrity checking
    """

    def __init__(self, database_path: Optional[str] = None):
        self.logger = get_logger(f"{__name__}.SRDComplianceService")

        # Database path for compliance data
        self.database_path = database_path or "data/srd_compliance.db"
        self._ensure_database_exists()

        # Official SRD sources (this would be configurable)
        self._official_sources = self._load_official_sources()

        # Compliance rules
        self._compliance_rules = self._load_compliance_rules()

    def _ensure_database_exists(self) -> None:
        """Ensure the compliance database exists with proper schema."""
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()

            # Create audit trail table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER,
                    entity_name TEXT NOT NULL,
                    user TEXT NOT NULL,
                    details TEXT NOT NULL,
                    compliance_status TEXT NOT NULL
                )
            """)

            # Create compliance status table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS compliance_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    last_verified TEXT NOT NULL,
                    verification_hash TEXT NOT NULL,
                    compliance_status TEXT NOT NULL,
                    issues TEXT,
                    UNIQUE(entity_type, entity_id)
                )
            """)

            # Create data sources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL UNIQUE,
                    source_url TEXT NOT NULL,
                    publication_date TEXT NOT NULL,
                    version TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    is_official BOOLEAN NOT NULL DEFAULT 1,
                    attribution_required BOOLEAN NOT NULL DEFAULT 1,
                    last_verified TEXT NOT NULL,
                    UNIQUE(source_name, version)
                )
            """)

            conn.commit()

    def _load_official_sources(self) -> Dict[str, DataSource]:
        """Load official SRD data sources."""
        # This would typically load from a configuration file
        # For now, we'll define the main official sources
        return {
            "dnd_5_1_srd": DataSource(
                source_name="Dungeons & Dragons 5.1 SRD",
                source_url="https://dnd.wizards.com/resources/systems-reference-document",
                publication_date=datetime(2023, 1, 1),  # Approximate date
                version="5.1",
                checksum="",  # Would be calculated from actual source
                is_official=True,
                attribution_required=True,
            ),
            "players_handbook_srd": DataSource(
                source_name="Player's Handbook SRD",
                source_url="https://dnd.wizards.com/resources/systems-reference-document",
                publication_date=datetime(2014, 8, 19),
                version="5.0",
                checksum="",  # Would be calculated from actual source
                is_official=True,
                attribution_required=True,
            ),
        }

    def _load_compliance_rules(self) -> Dict[str, Any]:
        """Load compliance rules and restrictions."""
        return {
            "usage_restrictions": [
                "Non-commercial use only",
                "Must attribute to Wizards of the Coast",
                "Cannot use for commercial products",
                "Cannot create derivative works for commercial use",
                "Must include proper copyright notices",
            ],
            "attribution_requirements": [
                "© 2023 Wizards of the Coast LLC",
                "Dungeons & Dragons, D&D, their respective logos, and all Wizards titles and characters are property of Wizards of the Coast LLC",
                "System Reference Document 5.1",
            ],
            "data_usage_limits": {
                "max_data_export": 1000,  # Max records that can be exported
                "require_verification": True,  # All data must be verified
                "audit_required": True,  # All usage must be audited
            },
        }

    def verify_data_compliance(
        self, data: Any, entity_type: str, user: str = "system"
    ) -> ComplianceCheckResult:
        """
        Verify compliance for a piece of SRD data.

        Args:
            data: The data object to verify (Monster, Spell, Weapon)
            entity_type: Type of entity ("monster", "spell", "weapon")
            user: User performing the verification

        Returns:
            ComplianceCheckResult with verification results
        """
        issues = []
        warnings = []
        recommendations = []

        # Check if data has compliance information
        if not hasattr(data, "srd_compliance"):
            issues.append("Missing SRD compliance information")
            return ComplianceCheckResult(
                is_compliant=False, issues=issues, check_type="compliance_verification"
            )

        compliance = data.srd_compliance

        # Verify data source
        source_issues = self._verify_data_source(data.data_source)
        issues.extend(source_issues)

        # Check compliance information
        if not compliance.data_source:
            issues.append("Missing data source information")
        elif compliance.data_source not in self._official_sources:
            warnings.append(
                f"Data source '{compliance.data_source}' not in official sources list"
            )

        if not compliance.license_version:
            issues.append("Missing license version information")

        if not compliance.verification_hash:
            issues.append("Missing verification hash")

        # Check if data is within acceptable usage limits
        usage_issues = self._check_usage_limits(data, entity_type)
        issues.extend(usage_issues)

        # Generate verification hash and compare
        current_hash = self._calculate_verification_hash(data, entity_type)
        if compliance.verification_hash != current_hash:
            issues.append("Verification hash mismatch - data may have been altered")

        # Create audit entry
        audit_entry = AuditEntry(
            action="compliance_verification",
            entity_type=entity_type,
            entity_id=getattr(data, f"{entity_type}_id", None),
            entity_name=getattr(data, f"{entity_type}_name", str(data)),
            user=user,
            details={
                "found_issues": len(issues),
                "found_warnings": len(warnings),
                "verification_hash": current_hash,
            },
            compliance_status="compliant" if not issues else "non_compliant",
        )

        self._save_audit_entry(audit_entry)

        # Determine overall compliance
        is_compliant = len(issues) == 0

        # Generate recommendations
        if warnings:
            recommendations.append("Review warnings for potential improvements")
        if issues:
            recommendations.append("Address compliance issues before using data")

        return ComplianceCheckResult(
            is_compliant=is_compliant,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            check_type="compliance_verification",
            details={
                "entity_type": entity_type,
                "entity_id": getattr(data, f"{entity_type}_id", None),
                "verification_hash": current_hash,
                "audit_id": self._get_last_audit_id(),
            },
        )

    def _verify_data_source(self, data_source: DataSource) -> List[str]:
        """Verify data source information."""
        issues = []

        if not data_source.source_name:
            issues.append("Missing source name")
            return issues

        # Check if it's an official source
        official_source = self._official_sources.get(
            data_source.source_name.lower().replace(" ", "_")
        )
        if not official_source:
            issues.append(
                f"Source '{data_source.source_name}' not recognized as official"
            )
        else:
            # Verify source details match
            if data_source.source_url != official_source.source_url:
                issues.append("Source URL does not match official source")
            if data_source.version != official_source.version:
                issues.append("Source version does not match official source")

        return issues

    def _check_usage_limits(self, data: Any, entity_type: str) -> List[str]:
        """Check if data usage is within acceptable limits."""
        issues = []

        # This would check against usage quotas, export limits, etc.
        # For now, we'll just do basic validation

        if hasattr(data, "is_active") and not data.is_active:
            issues.append("Data is marked as inactive")

        return issues

    def _calculate_verification_hash(self, data: Any, entity_type: str) -> str:
        """Calculate verification hash for data integrity."""
        # Create a deterministic string representation of the data
        data_str = ""

        # Add core data fields
        if hasattr(data, f"{entity_type}_name"):
            data_str += getattr(data, f"{entity_type}_name")

        # Add other important fields based on entity type
        if entity_type == "monster":
            data_str += str(data.armor_class) + data.hit_points
        elif entity_type == "spell":
            data_str += str(data.level) + data.school
        elif entity_type == "weapon":
            data_str += data.category + data.damage

        # Add source information
        if hasattr(data, "data_source"):
            data_str += data.data_source.source_name + data.data_source.version

        # Create SHA256 hash
        return f"sha256:{hashlib.sha256(data_str.encode()).hexdigest()}"

    def _save_audit_entry(self, entry: AuditEntry) -> None:
        """Save audit entry to database."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO audit_trail
                (timestamp, action, entity_type, entity_id, entity_name, user, details, compliance_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry.timestamp.isoformat(),
                    entry.action,
                    entry.entity_type,
                    entry.entity_id,
                    entry.entity_name,
                    entry.user,
                    json.dumps(entry.details),
                    entry.compliance_status,
                ),
            )

            conn.commit()

    def _get_last_audit_id(self) -> Optional[int]:
        """Get the ID of the last audit entry."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(id) FROM audit_trail")
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
        except Exception:
            return None

    def get_compliance_status(
        self, entity_type: str, entity_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get compliance status for a specific entity."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM compliance_status
                    WHERE entity_type = ? AND entity_id = ?
                """,
                    (entity_type, entity_id),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "entity_type": row[1],
                        "entity_id": row[2],
                        "last_verified": row[3],
                        "verification_hash": row[4],
                        "compliance_status": row[5],
                        "issues": json.loads(row[6]) if row[6] else None,
                    }
        except Exception as e:
            self.logger.error("Failed to get compliance status", error=str(e))

        return None

    def get_audit_trail(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit trail entries."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM audit_trail WHERE 1=1"
                params = []

                if entity_type:
                    query += " AND entity_type = ?"
                    params.append(entity_type)

                if entity_id:
                    query += " AND entity_id = ?"
                    params.append(entity_id)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                audit_trail = []
                for row in rows:
                    audit_trail.append(
                        {
                            "id": row[0],
                            "timestamp": row[1],
                            "action": row[2],
                            "entity_type": row[3],
                            "entity_id": row[4],
                            "entity_name": row[5],
                            "user": row[6],
                            "details": json.loads(row[7]),
                            "compliance_status": row[8],
                        }
                    )

                return audit_trail

        except Exception as e:
            self.logger.error("Failed to get audit trail", error=str(e))
            return []

    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                # Get audit statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_entries,
                        COUNT(CASE WHEN compliance_status = 'compliant' THEN 1 END) as compliant_entries,
                        COUNT(CASE WHEN compliance_status = 'non_compliant' THEN 1 END) as non_compliant_entries,
                        MAX(timestamp) as last_audit
                    FROM audit_trail
                """)

                stats = cursor.fetchone()

                # Get compliance issues
                cursor.execute("""
                    SELECT entity_type, COUNT(*) as issue_count
                    FROM audit_trail
                    WHERE compliance_status = 'non_compliant'
                    GROUP BY entity_type
                """)

                issues_by_type = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "report_generated": datetime.utcnow().isoformat(),
                    "audit_statistics": {
                        "total_entries": stats[0],
                        "compliant_entries": stats[1],
                        "non_compliant_entries": stats[2],
                        "compliance_rate": (stats[1] / stats[0]) * 100
                        if stats[0] > 0
                        else 0,
                        "last_audit": stats[3],
                    },
                    "issues_by_type": issues_by_type,
                    "compliance_rules": self._compliance_rules,
                    "official_sources": [
                        {
                            "name": source.source_name,
                            "version": source.version,
                            "url": source.source_url,
                        }
                        for source in self._official_sources.values()
                    ],
                }

        except Exception as e:
            self.logger.error("Failed to generate compliance report", error=str(e))
            return {"error": "Failed to generate compliance report", "details": str(e)}

    def add_data_source(self, source: DataSource, user: str = "system") -> bool:
        """Add a new data source to the compliance database."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO data_sources
                    (source_name, source_url, publication_date, version, checksum,
                     is_official, attribution_required, last_verified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        source.source_name,
                        source.source_url,
                        source.publication_date.isoformat(),
                        source.version,
                        source.checksum,
                        source.is_official,
                        source.attribution_required,
                        datetime.utcnow().isoformat(),
                    ),
                )

                conn.commit()

                # Create audit entry
                audit_entry = AuditEntry(
                    action="data_source_added",
                    entity_type="data_source",
                    entity_name=source.source_name,
                    user=user,
                    details={"version": source.version},
                    compliance_status="verified",
                )

                self._save_audit_entry(audit_entry)

                self.logger.info("Data source added", source_name=source.source_name)
                return True

        except Exception as e:
            self.logger.error("Failed to add data source", error=str(e))
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the SRD compliance service."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                # Check database health
                cursor.execute("SELECT COUNT(*) FROM audit_trail")
                audit_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM data_sources")
                source_count = cursor.fetchone()[0]

                return {
                    "status": "healthy",
                    "database_connected": True,
                    "audit_entries": audit_count,
                    "data_sources": source_count,
                    "official_sources_loaded": len(self._official_sources),
                    "compliance_rules_loaded": len(self._compliance_rules),
                }

        except Exception as e:
            return {"status": "unhealthy", "database_connected": False, "error": str(e)}


# Global SRD compliance service instance
srd_compliance_service = SRDComplianceService()

# Alias for backward compatibility with tests
ComplianceResult = ComplianceCheckResult
