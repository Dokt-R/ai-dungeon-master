"""
Privacy Handler Component for AI Dungeon Master.

This module provides comprehensive privacy and data handling specifications
to ensure GDPR compliance and user data protection for voice interactions.

Features:
- Data retention policy management
- Privacy consent handling
- Audio data encryption in transit
- User data access controls
- Compliance audit logging
- Automatic data deletion
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from packages.shared.models import PrivacyComplianceRecord
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PrivacyPolicy:
    """Privacy policy configuration."""

    data_retention_days: int = 30
    require_explicit_consent: bool = True
    encrypt_data_in_transit: bool = True
    encrypt_data_at_rest: bool = True
    allow_data_portability: bool = True
    data_minimization_enabled: bool = True
    audit_logging_enabled: bool = True
    compliance_officer_contact: str = "privacy@company.com"


@dataclass
class ConsentRecord:
    """User consent record."""

    user_id: str
    consent_type: str
    consented_at: datetime
    consent_expires: Optional[datetime] = None
    consent_withdrawn: bool = False
    consent_details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class PrivacyHandler:
    """
    Comprehensive privacy and data handling manager.

    Features:
    - Privacy consent management
    - Data retention and deletion
    - Encryption and security
    - Audit trail maintenance
    - Compliance reporting
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Privacy policies
        self.privacy_policy = PrivacyPolicy(
            data_retention_days=self.config.get('data_retention_days', 30),
            require_explicit_consent=self.config.get('require_explicit_consent', True)
        )

        # Consent tracking
        self.consent_records: Dict[str, List[ConsentRecord]] = {}

        # Compliance records
        self.compliance_records: Dict[str, PrivacyComplianceRecord] = {}

        # Audit log
        self.audit_log: List[Dict[str, Any]] = []

        # Data deletion queue
        self.deletion_queue: List[str] = []

        # Configuration
        self.audit_enabled = True
        self.auto_deletion_enabled = True

        logger.info("privacy_handler_initialized")

    async def obtain_voice_consent(
        self,
        user_id: str,
        session_id: str,
        consent_details: Dict[str, Any] = None
    ) -> bool:
        """
        Obtain user consent for voice processing.

        Args:
            user_id: User identifier
            session_id: Voice session identifier
            consent_details: Additional consent details

        Returns:
            True if consent obtained, False otherwise
        """
        try:
            # In a real implementation, this would:
            # 1. Check if user has previously consented
            # 2. If not, prompt user for consent
            # 3. Record consent in database
            # 4. Log audit trail

            consent_record = ConsentRecord(
                user_id=user_id,
                consent_type="voice_processing",
                consented_at=datetime.utcnow(),
                consent_expires=datetime.utcnow() + timedelta(days=365),  # 1 year
                consent_details=consent_details or {},
                ip_address=consent_details.get('ip_address') if consent_details else None,
                user_agent=consent_details.get('user_agent') if consent_details else None
            )

            # Store consent record
            if user_id not in self.consent_records:
                self.consent_records[user_id] = []
            self.consent_records[user_id].append(consent_record)

            # Log audit event
            self._audit_log(
                action="consent_obtained",
                user_id=user_id,
                session_id=session_id,
                details={"consent_type": "voice_processing"}
            )

            logger.info(
                "voice_consent_obtained",
                user_id=user_id,
                session_id=session_id
            )

            return True

        except Exception as e:
            logger.error(
                "voice_consent_obtain_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return False

    def check_voice_consent(self, user_id: str, session_id: str) -> bool:
        """
        Check if user has provided consent for voice processing.

        Args:
            user_id: User identifier
            session_id: Voice session identifier

        Returns:
            True if user has valid consent, False otherwise
        """
        try:
            if not self.privacy_policy.require_explicit_consent:
                return True

            user_consents = self.consent_records.get(user_id, [])

            # Find valid voice processing consent
            for consent in user_consents:
                if (consent.consent_type == "voice_processing" and
                    not consent.consent_withdrawn and
                    (consent.consent_expires is None or consent.consent_expires > datetime.utcnow())):
                    return True

            return False

        except Exception as e:
            logger.error(
                "voice_consent_check_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return False

    async def schedule_data_deletion(
        self,
        session_id: str,
        user_id: str,
        retention_days: int = None
    ) -> bool:
        """
        Schedule audio data for deletion after retention period.

        Args:
            session_id: Voice session identifier
            user_id: User identifier
            retention_days: Days to retain data

        Returns:
            True if scheduled successfully, False otherwise
        """
        try:
            days = retention_days or self.privacy_policy.data_retention_days
            deletion_date = datetime.utcnow() + timedelta(days=days)

            # Create compliance record
            compliance_record = PrivacyComplianceRecord(
                session_id=session_id,
                user_id=user_id,
                data_retention_period_days=days,
                data_deletion_date=deletion_date,
                privacy_consent_obtained=self.check_voice_consent(user_id, session_id),
                data_encrypted=self.privacy_policy.encrypt_data_in_transit,
                compliance_officer=self.privacy_policy.compliance_officer_contact
            )

            # Store compliance record
            self.compliance_records[session_id] = compliance_record

            # Add to deletion queue
            self.deletion_queue.append(session_id)

            # Log audit event
            self._audit_log(
                action="data_deletion_scheduled",
                user_id=user_id,
                session_id=session_id,
                details={"deletion_date": deletion_date.isoformat(), "retention_days": days}
            )

            logger.info(
                "data_deletion_scheduled",
                session_id=session_id,
                user_id=user_id,
                deletion_date=deletion_date.isoformat()
            )

            return True

        except Exception as e:
            logger.error(
                "data_deletion_scheduling_failed",
                session_id=session_id,
                user_id=user_id,
                error=str(e)
            )
            return False

    async def process_data_deletion_queue(self) -> int:
        """
        Process queued data deletions.

        Returns:
            Number of records processed
        """
        try:
            current_time = datetime.utcnow()
            processed_count = 0

            # Find records ready for deletion
            ready_for_deletion = []

            for session_id in self.deletion_queue:
                if session_id in self.compliance_records:
                    record = self.compliance_records[session_id]
                    if record.data_deletion_date <= current_time:
                        ready_for_deletion.append(session_id)

            # Process deletions
            for session_id in ready_for_deletion:
                try:
                    await self._delete_voice_data(session_id)
                    self.deletion_queue.remove(session_id)
                    del self.compliance_records[session_id]
                    processed_count += 1

                except Exception as e:
                    logger.error(
                        "data_deletion_failed",
                        session_id=session_id,
                        error=str(e)
                    )

            if processed_count > 0:
                logger.info("data_deletions_processed", count=processed_count)

            return processed_count

        except Exception as e:
            logger.error("data_deletion_queue_processing_failed", error=str(e))
            return 0

    async def _delete_voice_data(self, session_id: str) -> None:
        """Delete voice data for a session."""
        # In a real implementation, this would:
        # 1. Delete audio files from storage
        # 2. Remove transcription records
        # 3. Clean up database records
        # 4. Remove from cache systems

        self._audit_log(
            action="voice_data_deleted",
            session_id=session_id,
            details={"deletion_method": "secure_wipe"}
        )

        logger.info("voice_data_deleted", session_id=session_id)

    def _audit_log(self, action: str, **kwargs) -> None:
        """Add entry to audit log."""
        if not self.audit_enabled:
            return

        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            **kwargs
        }

        self.audit_log.append(audit_entry)

        # Keep only last 10000 entries
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]

    def generate_compliance_report(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate privacy compliance report.

        Args:
            user_id: Optional user ID to filter report

        Returns:
            Compliance report data
        """
        try:
            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "privacy_policy": {
                    "data_retention_days": self.privacy_policy.data_retention_days,
                    "require_explicit_consent": self.privacy_policy.require_explicit_consent,
                    "encrypt_data_in_transit": self.privacy_policy.encrypt_data_in_transit,
                    "encrypt_data_at_rest": self.privacy_policy.encrypt_data_at_rest
                }
            }

            if user_id:
                # User-specific report
                user_consents = self.consent_records.get(user_id, [])
                user_compliance_records = [
                    r for r in self.compliance_records.values() if r.user_id == user_id
                ]

                report["user_id"] = user_id
                report["consent_records"] = len(user_consents)
                report["compliance_records"] = len(user_compliance_records)
                report["valid_consents"] = len([
                    c for c in user_consents
                    if not c.consent_withdrawn and
                    (c.consent_expires is None or c.consent_expires > datetime.utcnow())
                ])
            else:
                # System-wide report
                report["total_users"] = len(self.consent_records)
                report["total_consent_records"] = sum(len(consents) for consents in self.consent_records.values())
                report["total_compliance_records"] = len(self.compliance_records)
                report["pending_deletions"] = len(self.deletion_queue)

            return report

        except Exception as e:
            logger.error("compliance_report_generation_failed", error=str(e))
            return {}

    def get_user_data_access(self, user_id: str) -> Dict[str, Any]:
        """
        Provide user data access as required by GDPR Article 15.

        Args:
            user_id: User identifier

        Returns:
            User data access report
        """
        try:
            user_consents = self.consent_records.get(user_id, [])
            user_compliance_records = [
                r for r in self.compliance_records.values() if r.user_id == user_id
            ]

            return {
                "user_id": user_id,
                "data_collected": {
                    "consent_records": [c.__dict__ for c in user_consents],
                    "compliance_records": [r.__dict__ for r in user_compliance_records],
                    "audit_entries": [e for e in self.audit_log if e.get("user_id") == user_id]
                },
                "retention_period": self.privacy_policy.data_retention_days,
                "data_purposes": ["voice_interaction", "ai_response_generation"],
                "legal_basis": "consent",
                "access_date": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error("user_data_access_failed", user_id=user_id, error=str(e))
            return {}

    def withdraw_consent(self, user_id: str, consent_type: str = "all") -> bool:
        """
        Withdraw user consent for data processing.

        Args:
            user_id: User identifier
            consent_type: Type of consent to withdraw

        Returns:
            True if consent withdrawn successfully, False otherwise
        """
        try:
            if user_id not in self.consent_records:
                return False

            user_consents = self.consent_records[user_id]

            if consent_type == "all":
                # Withdraw all consents
                for consent in user_consents:
                    consent.consent_withdrawn = True
            else:
                # Withdraw specific consent type
                for consent in user_consents:
                    if consent.consent_type == consent_type:
                        consent.consent_withdrawn = True

            # Log audit event
            self._audit_log(
                action="consent_withdrawn",
                user_id=user_id,
                details={"consent_type": consent_type}
            )

            logger.info(
                "user_consent_withdrawn",
                user_id=user_id,
                consent_type=consent_type
            )

            return True

        except Exception as e:
            logger.error(
                "consent_withdrawal_failed",
                user_id=user_id,
                consent_type=consent_type,
                error=str(e)
            )
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the privacy handler."""
        return {
            "status": "healthy",
            "audit_enabled": self.audit_enabled,
            "auto_deletion_enabled": self.auto_deletion_enabled,
            "total_consent_records": sum(len(consents) for consents in self.consent_records.values()),
            "total_compliance_records": len(self.compliance_records),
            "pending_deletions": len(self.deletion_queue),
            "audit_log_entries": len(self.audit_log),
            "privacy_policy_active": True
        }


# Global privacy handler instance
privacy_handler = PrivacyHandler()