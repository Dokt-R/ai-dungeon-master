"""
Unit tests for SRD Compliance Service.

Tests cover:
- Compliance verification for monsters, spells, and weapons
- License validation and restrictions
- Data source verification
- Audit trail functionality
- Compliance reporting
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from packages.shared.models import Monster, Spell, Weapon, SRDCompliance, DataSource
from packages.backend.components.srd_compliance_service import (
    SRDComplianceService,
    ComplianceResult,
    LicenseRestriction
)


class TestSRDComplianceService:
    """Test cases for SRD Compliance Service."""

    @pytest.fixture
    def compliance_service(self):
        """Create a fresh compliance service for each test."""
        return SRDComplianceService()

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
            attribution_required=True
        )

    @pytest.fixture
    def sample_compliance(self, sample_data_source):
        """Create a sample compliance record for testing."""
        return SRDCompliance(
            data_source="D&D 5.1 SRD",
            license_version="5.1",
            usage_restrictions=[
                "Must include Wizards of the Coast attribution",
                "Cannot be used in commercial products"
            ],
            last_verified=datetime.utcnow(),
            verification_hash="test_hash_123",
            compliance_officer="Test Officer",
            audit_trail=["Initial import"]
        )

    @pytest.fixture
    def sample_monster(self, sample_compliance, sample_data_source):
        """Create a sample monster for testing."""
        return Monster(
            monster_name="Test Monster",
            armor_class=15,
            hit_points="45 (7d8 + 14)",
            strength=16,
            dexterity=14,
            constitution=14,
            intelligence=10,
            wisdom=12,
            charisma=8,
            challenge_rating="2",
            actions="Test Action: +5 to hit, 1d8+3 damage",
            special_abilities="Test Ability: Does test things",
            description="A test monster for unit testing",
            srd_compliance=sample_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True
        )

    def test_verify_data_compliance_monster_valid(self, compliance_service, sample_monster):
        """Test compliance verification for a valid monster."""
        result = compliance_service.verify_data_compliance(
            sample_monster, "monster", "test_user"
        )

        assert isinstance(result, ComplianceResult)
        assert result.is_compliant is True
        assert len(result.issues) == 0
        assert result.verification_date is not None

    def test_verify_data_compliance_monster_invalid_source(self, compliance_service, sample_monster):
        """Test compliance verification for monster with invalid source."""
        sample_monster.data_source.is_official = False

        result = compliance_service.verify_data_compliance(
            sample_monster, "monster", "test_user"
        )

        assert result.is_compliant is False
        assert len(result.issues) > 0
        assert any("official" in issue.lower() for issue in result.issues)

    def test_verify_data_compliance_monster_expired(self, compliance_service, sample_monster):
        """Test compliance verification for monster with expired verification."""
        sample_monster.srd_compliance.last_verified = datetime(2020, 1, 1)

        result = compliance_service.verify_data_compliance(
            sample_monster, "monster", "test_user"
        )

        assert result.is_compliant is False
        assert len(result.issues) > 0

    def test_verify_data_compliance_spell_valid(self, compliance_service, sample_compliance, sample_data_source):
        """Test compliance verification for a valid spell."""
        spell = Spell(
            spell_name="Test Spell",
            level=3,
            school="Evocation",
            casting_time="1 action",
            range="120 feet",
            components="V, S, M (a handful of sand)",
            duration="Concentration, up to 1 minute",
            description="A test spell for unit testing",
            at_higher_levels="",
            classes=["Wizard", "Sorcerer"],
            srd_compliance=sample_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True
        )

        result = compliance_service.verify_data_compliance(spell, "spell", "test_user")

        assert result.is_compliant is True
        assert len(result.issues) == 0

    def test_verify_data_compliance_weapon_valid(self, compliance_service, sample_compliance, sample_data_source):
        """Test compliance verification for a valid weapon."""
        weapon = Weapon(
            weapon_name="Test Weapon",
            category="Simple Melee Weapons",
            cost="2 gp",
            damage="1d8 piercing",
            weight="3 lb.",
            properties=["Finesse", "Thrown (range 20/60)"],
            description="A test weapon for unit testing",
            srd_compliance=sample_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True
        )

        result = compliance_service.verify_data_compliance(weapon, "weapon", "test_user")

        assert result.is_compliant is True
        assert len(result.issues) == 0

    def test_verify_data_compliance_invalid_type(self, compliance_service, sample_monster):
        """Test compliance verification with invalid data type."""
        with pytest.raises(ValueError, match="Unsupported data type"):
            compliance_service.verify_data_compliance(sample_monster, "invalid_type", "test_user")

    def test_generate_compliance_report(self, compliance_service, sample_monster):
        """Test compliance report generation."""
        report = compliance_service.generate_compliance_report([sample_monster])

        assert isinstance(report, dict)
        assert "total_entities" in report
        assert "compliant_entities" in report
        assert "non_compliant_entities" in report
        assert "compliance_rate" in report
        assert "issues_summary" in report

    def test_check_license_restrictions(self, compliance_service, sample_compliance):
        """Test license restriction checking."""
        restrictions = compliance_service._check_license_restrictions(sample_compliance)

        assert isinstance(restrictions, list)
        # Should identify OGL restrictions
        assert len(restrictions) > 0

    def test_validate_data_source(self, compliance_service, sample_data_source):
        """Test data source validation."""
        issues = compliance_service._validate_data_source(sample_data_source)

        assert isinstance(issues, list)
        # Official SRD source should have no issues
        assert len(issues) == 0

    def test_validate_data_source_unofficial(self, compliance_service, sample_data_source):
        """Test data source validation with unofficial source."""
        sample_data_source.is_official = False
        sample_data_source.source_name = "Homebrew Content"

        issues = compliance_service._validate_data_source(sample_data_source)

        assert len(issues) > 0
        assert any("official" in issue.lower() for issue in issues)

    def test_calculate_compliance_hash(self, compliance_service, sample_monster):
        """Test compliance hash calculation."""
        hash_value = compliance_service._calculate_compliance_hash(sample_monster)

        assert isinstance(hash_value, str)
        assert len(hash_value) > 0

        # Hash should be consistent
        hash_value2 = compliance_service._calculate_compliance_hash(sample_monster)
        assert hash_value == hash_value2

    def test_update_audit_trail(self, compliance_service, sample_compliance):
        """Test audit trail updates."""
        original_length = len(sample_compliance.audit_trail)

        updated_compliance = compliance_service._update_audit_trail(
            sample_compliance, "test_action", "test_user"
        )

        assert len(updated_compliance.audit_trail) == original_length + 1
        assert "test_action" in updated_compliance.audit_trail[-1]
        assert "test_user" in updated_compliance.audit_trail[-1]

    @patch('packages.backend.components.srd_compliance_service.datetime')
    def test_is_verification_expired(self, mock_datetime, compliance_service):
        """Test verification expiration checking."""
        # Set current time to 2024
        mock_datetime.utcnow.return_value = datetime(2024, 1, 1)

        # Test with recent verification (should not be expired)
        recent_verification = datetime(2023, 12, 1)
        assert not compliance_service._is_verification_expired(recent_verification)

        # Test with old verification (should be expired)
        old_verification = datetime(2020, 1, 1)
        assert compliance_service._is_verification_expired(old_verification)

    def test_get_license_requirements(self, compliance_service):
        """Test license requirements retrieval."""
        requirements = compliance_service.get_license_requirements()

        assert isinstance(requirements, dict)
        assert "attribution" in requirements
        assert "usage_restrictions" in requirements
        assert "compliance_officer" in requirements

    def test_health_check(self, compliance_service):
        """Test compliance service health check."""
        health = compliance_service.health_check()

        assert isinstance(health, dict)
        assert "status" in health
        assert "last_verification_check" in health
        assert "total_compliance_checks" in health


class TestComplianceResult:
    """Test cases for ComplianceResult model."""

    def test_compliance_result_creation(self):
        """Test ComplianceResult creation."""
        issues = ["Issue 1", "Issue 2"]
        result = ComplianceResult(
            is_compliant=False,
            issues=issues,
            verification_date=datetime.utcnow()
        )

        assert result.is_compliant is False
        assert result.issues == issues
        assert result.verification_date is not None

    def test_compliance_result_defaults(self):
        """Test ComplianceResult default values."""
        result = ComplianceResult()

        assert result.is_compliant is True
        assert result.issues == []
        assert result.verification_date is None


class TestLicenseRestriction:
    """Test cases for LicenseRestriction enum."""

    def test_license_restriction_values(self):
        """Test LicenseRestriction enum values."""
        assert LicenseRestriction.ATTRIBUTION_REQUIRED.value == "attribution_required"
        assert LicenseRestriction.NO_COMMERCIAL_USE.value == "no_commercial_use"
        assert LicenseRestriction.OGL_COMPLIANCE.value == "ogl_compliance"

    def test_license_restriction_from_string(self):
        """Test creating LicenseRestriction from string."""
        restriction = LicenseRestriction("attribution_required")
        assert restriction == LicenseRestriction.ATTRIBUTION_REQUIRED