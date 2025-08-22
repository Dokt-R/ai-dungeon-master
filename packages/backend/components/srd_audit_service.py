"""
SRD Audit Service for D&D 5.1 System Reference Document.

This module provides audit logging and compliance monitoring for SRD data including:
- Usage logging for compliance monitoring
- Audit trail for data source verification
- Access tracking and reporting
- Compliance violation detection
- Audit report generation
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from packages.shared.models import Monster, Spell, Weapon
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Type of audit event."""
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    COMPLIANCE_CHECK = "compliance_check"
    IMPORT_OPERATION = "import_operation"
    EXPORT_OPERATION = "export_operation"
    BACKUP_OPERATION = "backup_operation"
    MIGRATION_OPERATION = "migration_operation"
    VERIFICATION_OPERATION = "verification_operation"


class ComplianceViolationType(Enum):
    """Type of compliance violation."""
    UNVERIFIED_SOURCE = "unverified_source"
    INVALID_CHECKSUM = "invalid_checksum"
    EXPIRED_VERIFICATION = "expired_verification"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MISSING_ATTRIBUTION = "missing_attribution"
    COMMERCIAL_USE_VIOLATION = "commercial_use_violation"


@dataclass
class AuditEvent:
    """Audit event record."""
    event_id: str
    event_type: AuditEventType
    entity_type: str
    entity_name: str
    user_id: str
    user_role: str
    timestamp: datetime
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]


@dataclass
class ComplianceViolation:
    """Compliance violation record."""
    violation_id: str
    violation_type: ComplianceViolationType
    entity_type: str
    entity_name: str
    description: str
    severity: str
    detected_at: datetime
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]


class SRDAuditService:
    """
    Service for audit logging and compliance monitoring.

    Features:
    - Comprehensive audit trail
    - Compliance violation tracking
    - Usage analytics and reporting
    - Access pattern analysis
    - Audit report generation
    """

    def __init__(self, audit_log_path: Optional[str] = None):
        self.logger = get_logger(f"{__name__}.SRDAuditService")
        self.audit_log_path = audit_log_path or "data/audit/srd_audit.log"
        self.violations_log_path = "data/audit/compliance_violations.log"

        # Ensure audit directories exist
        Path(self.audit_log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.violations_log_path).parent.mkdir(parents=True, exist_ok=True)

    def log_data_access(
        self,
        entity: Union[Monster, Spell, Weapon],
        user_id: str,
        user_role: str = "user",
        access_type: str = "read",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Log data access event."""
        entity_type = entity.__class__.__name__.lower()
        entity_name = getattr(entity, f"{entity_type}_name")

        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.DATA_ACCESS,
            entity_type=entity_type,
            entity_name=entity_name,
            user_id=user_id,
            user_role=user_role,
            timestamp=datetime.utcnow(),
            details={
                "access_type": access_type,
                "entity_id": getattr(entity, f"{entity_type}_id"),
                "data_source": entity.data_source.source_name,
                "compliance_status": entity.srd_compliance.data_source
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )

        self._write_audit_event(event)
        self.logger.info("Data access logged", event_id=event.event_id, entity_type=entity_type, user_id=user_id)

        return event.event_id

    def log_data_modification(
        self,
        entity: Union[Monster, Spell, Weapon],
        user_id: str,
        user_role: str = "admin",
        modification_type: str = "update",
        changes: Dict[str, Any] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Log data modification event."""
        entity_type = entity.__class__.__name__.lower()
        entity_name = getattr(entity, f"{entity_type}_name")

        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.DATA_MODIFICATION,
            entity_type=entity_type,
            entity_name=entity_name,
            user_id=user_id,
            user_role=user_role,
            timestamp=datetime.utcnow(),
            details={
                "modification_type": modification_type,
                "entity_id": getattr(entity, f"{entity_type}_id"),
                "changes": changes or {},
                "data_source": entity.data_source.source_name
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )

        self._write_audit_event(event)
        self.logger.info("Data modification logged", event_id=event.event_id, entity_type=entity_type, user_id=user_id)

        return event.event_id

    def log_compliance_check(
        self,
        entity: Union[Monster, Spell, Weapon],
        user_id: str,
        compliance_result: Dict[str, Any],
        user_role: str = "system",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Log compliance check event."""
        entity_type = entity.__class__.__name__.lower()
        entity_name = getattr(entity, f"{entity_type}_name")

        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.COMPLIANCE_CHECK,
            entity_type=entity_type,
            entity_name=entity_name,
            user_id=user_id,
            user_role=user_role,
            timestamp=datetime.utcnow(),
            details={
                "compliance_result": compliance_result,
                "entity_id": getattr(entity, f"{entity_type}_id"),
                "is_compliant": compliance_result.get("is_compliant", False),
                "issue_count": len(compliance_result.get("issues", []))
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )

        self._write_audit_event(event)
        self.logger.info("Compliance check logged", event_id=event.event_id, entity_type=entity_type, is_compliant=compliance_result.get("is_compliant", False))

        return event.event_id

    def log_import_operation(
        self,
        import_type: str,
        user_id: str,
        import_result: Dict[str, Any],
        user_role: str = "admin",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Log import operation event."""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=AuditEventType.IMPORT_OPERATION,
            entity_type="bulk_data",
            entity_name=f"import_{import_type}",
            user_id=user_id,
            user_role=user_role,
            timestamp=datetime.utcnow(),
            details={
                "import_type": import_type,
                "import_result": import_result,
                "total_records": import_result.get("total_records", 0),
                "successful_imports": import_result.get("successful_imports", 0),
                "failed_imports": import_result.get("failed_imports", 0),
                "processing_time": import_result.get("processing_time", 0)
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )

        self._write_audit_event(event)
        self.logger.info("Import operation logged", event_id=event.event_id, import_type=import_type, user_id=user_id)

        return event.event_id

    def log_compliance_violation(
        self,
        violation_type: ComplianceViolationType,
        entity: Union[Monster, Spell, Weapon],
        description: str,
        severity: str = "medium"
    ) -> str:
        """Log compliance violation."""
        entity_type = entity.__class__.__name__.lower()
        entity_name = getattr(entity, f"{entity_type}_name")

        violation = ComplianceViolation(
            violation_id=self._generate_event_id(),
            violation_type=violation_type,
            entity_type=entity_type,
            entity_name=entity_name,
            description=description,
            severity=severity,
            detected_at=datetime.utcnow(),
            resolved_at=None,
            resolution_notes=None
        )

        self._write_violation(violation)

        # Also log as audit event
        event = AuditEvent(
            event_id=violation.violation_id,
            event_type=AuditEventType.COMPLIANCE_CHECK,
            entity_type=entity_type,
            entity_name=entity_name,
            user_id="system",
            user_role="compliance_monitor",
            timestamp=datetime.utcnow(),
            details={
                "violation_type": violation_type.value,
                "description": description,
                "severity": severity,
                "entity_id": getattr(entity, f"{entity_type}_id")
            },
            ip_address=None,
            user_agent=None,
            session_id=None
        )

        self._write_audit_event(event)

        self.logger.warning("Compliance violation detected",
                           violation_id=violation.violation_id,
                           violation_type=violation_type.value,
                           entity_type=entity_type,
                           severity=severity)

        return violation.violation_id

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        random_suffix = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        return f"audit_{timestamp}_{random_suffix}"

    def _write_audit_event(self, event: AuditEvent) -> None:
        """Write audit event to log file."""
        try:
            log_entry = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "entity_type": event.entity_type,
                "entity_name": event.entity_name,
                "user_id": event.user_id,
                "user_role": event.user_role,
                "timestamp": event.timestamp.isoformat(),
                "details": event.details,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "session_id": event.session_id
            }

            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            self.logger.error("Failed to write audit event", error=str(e))

    def _write_violation(self, violation: ComplianceViolation) -> None:
        """Write compliance violation to log file."""
        try:
            violation_entry = {
                "violation_id": violation.violation_id,
                "violation_type": violation.violation_type.value,
                "entity_type": violation.entity_type,
                "entity_name": violation.entity_name,
                "description": violation.description,
                "severity": violation.severity,
                "detected_at": violation.detected_at.isoformat(),
                "resolved_at": violation.resolved_at.isoformat() if violation.resolved_at else None,
                "resolution_notes": violation.resolution_notes
            }

            with open(self.violations_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(violation_entry) + "\n")

        except Exception as e:
            self.logger.error("Failed to write compliance violation", error=str(e))

    def get_audit_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> List[AuditEvent]:
        """Get audit events with optional filtering."""
        events = []

        try:
            if not Path(self.audit_log_path).exists():
                return events

            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            log_entry = json.loads(line.strip())
                            event = AuditEvent(
                                event_id=log_entry["event_id"],
                                event_type=AuditEventType(log_entry["event_type"]),
                                entity_type=log_entry["entity_type"],
                                entity_name=log_entry["entity_name"],
                                user_id=log_entry["user_id"],
                                user_role=log_entry["user_role"],
                                timestamp=datetime.fromisoformat(log_entry["timestamp"]),
                                details=log_entry["details"],
                                ip_address=log_entry["ip_address"],
                                user_agent=log_entry["user_agent"],
                                session_id=log_entry["session_id"]
                            )

                            # Apply filters
                            if start_date and event.timestamp < start_date:
                                continue
                            if end_date and event.timestamp > end_date:
                                continue
                            if event_type and event.event_type != event_type:
                                continue
                            if user_id and event.user_id != user_id:
                                continue
                            if entity_type and event.entity_type != entity_type:
                                continue

                            events.append(event)

                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            self.logger.warning("Failed to parse audit log entry", error=str(e))
                            continue

        except Exception as e:
            self.logger.error("Failed to read audit events", error=str(e))

        return events

    def get_compliance_violations(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        violation_type: Optional[ComplianceViolationType] = None,
        resolved: Optional[bool] = None
    ) -> List[ComplianceViolation]:
        """Get compliance violations with optional filtering."""
        violations = []

        try:
            if not Path(self.violations_log_path).exists():
                return violations

            with open(self.violations_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            violation_entry = json.loads(line.strip())
                            violation = ComplianceViolation(
                                violation_id=violation_entry["violation_id"],
                                violation_type=ComplianceViolationType(violation_entry["violation_type"]),
                                entity_type=violation_entry["entity_type"],
                                entity_name=violation_entry["entity_name"],
                                description=violation_entry["description"],
                                severity=violation_entry["severity"],
                                detected_at=datetime.fromisoformat(violation_entry["detected_at"]),
                                resolved_at=datetime.fromisoformat(violation_entry["resolved_at"]) if violation_entry["resolved_at"] else None,
                                resolution_notes=violation_entry["resolution_notes"]
                            )

                            # Apply filters
                            if start_date and violation.detected_at < start_date:
                                continue
                            if end_date and violation.detected_at > end_date:
                                continue
                            if violation_type and violation.violation_type != violation_type:
                                continue
                            if resolved is not None:
                                is_resolved = violation.resolved_at is not None
                                if resolved != is_resolved:
                                    continue

                            violations.append(violation)

                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            self.logger.warning("Failed to parse violation log entry", error=str(e))
                            continue

        except Exception as e:
            self.logger.error("Failed to read compliance violations", error=str(e))

        return violations

    def generate_audit_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive audit report."""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get audit events
        all_events = self.get_audit_events(start_date=start_date, end_date=end_date)
        violations = self.get_compliance_violations(start_date=start_date, end_date=end_date)

        # Analyze events by type
        events_by_type = {}
        for event in all_events:
            event_type = event.event_type.value
            if event_type not in events_by_type:
                events_by_type[event_type] = 0
            events_by_type[event_type] += 1

        # Analyze events by user
        events_by_user = {}
        for event in all_events:
            user_id = event.user_id
            if user_id not in events_by_user:
                events_by_user[user_id] = 0
            events_by_user[user_id] += 1

        # Analyze violations by type
        violations_by_type = {}
        for violation in violations:
            violation_type = violation.violation_type.value
            if violation_type not in violations_by_type:
                violations_by_type[violation_type] = 0
            violations_by_type[violation_type] += 1

        # Analyze violations by severity
        violations_by_severity = {}
        for violation in violations:
            severity = violation.severity
            if severity not in violations_by_severity:
                violations_by_severity[severity] = 0
            violations_by_severity[severity] += 1

        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_days": (end_date - start_date).days
            },
            "summary": {
                "total_events": len(all_events),
                "total_violations": len(violations),
                "unique_users": len(events_by_user),
                "compliance_rate": ((len(all_events) - len(violations)) / len(all_events)) if all_events else 1.0
            },
            "events": {
                "by_type": events_by_type,
                "by_user": events_by_user,
                "top_users": sorted(events_by_user.items(), key=lambda x: x[1], reverse=True)[:10]
            },
            "violations": {
                "by_type": violations_by_type,
                "by_severity": violations_by_severity,
                "unresolved_count": len([v for v in violations if v.resolved_at is None])
            },
            "recommendations": self._generate_report_recommendations(all_events, violations)
        }

    def _generate_report_recommendations(
        self,
        events: List[AuditEvent],
        violations: List[ComplianceViolation]
    ) -> List[str]:
        """Generate recommendations based on audit data."""
        recommendations = []

        # Check for high violation rates
        if violations and events:
            violation_rate = len(violations) / len(events)
            if violation_rate > 0.1:
                recommendations.append("High compliance violation rate detected. Review data sources and user training.")

        # Check for unauthorized access patterns
        unauthorized_events = [e for e in events if e.details.get("access_type") == "unauthorized"]
        if unauthorized_events:
            recommendations.append("Unauthorized access attempts detected. Review access controls and user permissions.")

        # Check for frequent data modifications
        modification_events = [e for e in events if e.event_type == AuditEventType.DATA_MODIFICATION]
        if len(modification_events) > len(events) * 0.5:
            recommendations.append("High rate of data modifications. Consider implementing stricter change controls.")

        # Check for compliance check frequency
        compliance_events = [e for e in events if e.event_type == AuditEventType.COMPLIANCE_CHECK]
        if len(compliance_events) < len(events) * 0.1:
            recommendations.append("Low frequency of compliance checks. Increase automated compliance monitoring.")

        return recommendations

    def health_check(self) -> Dict[str, Any]:
        """Get health status of the audit service."""
        try:
            audit_log_exists = Path(self.audit_log_path).exists()
            violations_log_exists = Path(self.violations_log_path).exists()

            # Get log file sizes
            audit_size = Path(self.audit_log_path).stat().st_size if audit_log_exists else 0
            violations_size = Path(self.violations_log_path).stat().st_size if violations_log_exists else 0

            # Count recent events (last 24 hours)
            recent_events = self.get_audit_events(
                start_date=datetime.utcnow() - timedelta(hours=24)
            )

            return {
                "status": "healthy" if audit_log_exists else "degraded",
                "audit_log_exists": audit_log_exists,
                "violations_log_exists": violations_log_exists,
                "audit_log_size_bytes": audit_size,
                "violations_log_size_bytes": violations_size,
                "recent_events_count": len(recent_events),
                "service_ready": True,
                "last_check": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service_ready": False,
                "last_check": datetime.utcnow().isoformat()
            }


# Global SRD audit service instance
srd_audit_service = SRDAuditService()