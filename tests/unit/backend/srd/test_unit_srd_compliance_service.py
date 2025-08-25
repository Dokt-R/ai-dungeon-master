"""
Unit tests for SRD Compliance Service.

Tests cover:
- Compliance verification for monsters, spells, and weapons
- License validation and restrictions
- Data source verification
- Audit trail functionality
- Compliance reporting
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from packages.backend.components.srd_compliance_service import (
    ComplianceResult,
    LicenseRestriction,
    SRDComplianceService,
)
from packages.shared.models import DataSource, Monster, Spell, SRDCompliance, Weapon


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
            source_name="Dungeons & Dragons 5.1 SRD",
            source_url="https://dnd.wizards.com/resources/systems-reference-document",
            publication_date=datetime(2023, 1, 1),
            version="5.1",
            checksum="test_checksum_123",
            is_official=True,
            attribution_required=True,
        )

    @pytest.fixture
    def sample_compliance(self, sample_data_source):
        """Create a sample compliance record for testing."""
        return SRDCompliance(
            data_source=sample_data_source.source_name,
            license_version="5.1",
            usage_restrictions=[
                "Must include Wizards of the Coast attribution",
                "Cannot be used in commercial products",
            ],
            last_verified=datetime.utcnow(),
            verification_hash="sha256:440ac33522c31e3278fa63785e3191a798d7f4e56cacbe3eac0508abeed0d755",
            compliance_officer="Test Officer",
            audit_trail=[
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "initial_import",
                    "details": "Initial import",
                }
            ],
        )

    @pytest.fixture
    def sample_spell_compliance(self, sample_data_source):
        """Create a sample compliance record for spell testing."""
        return SRDCompliance(
            data_source=sample_data_source.source_name,
            license_version="5.1",
            usage_restrictions=[
                "Must include Wizards of the Coast attribution",
                "Cannot be used in commercial products",
            ],
            last_verified=datetime.utcnow(),
            verification_hash="sha256:1e2b792b8405d839e036ec274cdd8af3845b7ba9c6a3468ca74f783530db27c7",
            compliance_officer="Test Officer",
            audit_trail=[
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "initial_import",
                    "details": "Initial import",
                }
            ],
        )

    @pytest.fixture
    def sample_weapon_compliance(self, sample_data_source):
        """Create a sample compliance record for weapon testing."""
        return SRDCompliance(
            data_source=sample_data_source.source_name,
            license_version="5.1",
            usage_restrictions=[
                "Must include Wizards of the Coast attribution",
                "Cannot be used in commercial products",
            ],
            last_verified=datetime.utcnow(),
            verification_hash="sha256:b53e9a68b5c10c6b9e7e6af0a06404caf2ca5c7846db4322d2f2306dad1616fa",
            compliance_officer="Test Officer",
            audit_trail=[
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "initial_import",
                    "details": "Initial import",
                }
            ],
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
            is_active=True,
        )

    def test_verify_data_compliance_monster_valid(
        self, compliance_service, sample_monster
    ):
        """Test compliance verification for a valid monster."""
        result = compliance_service.verify_data_compliance(
            sample_monster, "monster", "test_user"
        )

        assert isinstance(result, ComplianceResult)
        assert result.is_compliant is True
        assert len(result.issues) == 0
        assert result.timestamp is not None

    def test_verify_data_compliance_monster_invalid_source(
        self, compliance_service, sample_monster
    ):
        """Test compliance verification for monster with invalid source."""
        sample_monster.data_source.source_name = "Invalid Source Name"
        sample_monster.data_source.is_official = False

        result = compliance_service.verify_data_compliance(
            sample_monster, "monster", "test_user"
        )

        assert result.is_compliant is False
        assert len(result.issues) > 0
        assert any("not recognized as official" in issue for issue in result.issues)

    def test_verify_data_compliance_monster_expired(
        self, compliance_service, sample_monster
    ):
        """Test compliance verification for monster with expired verification."""
        sample_monster.srd_compliance.last_verified = datetime(2020, 1, 1)

        result = compliance_service.verify_data_compliance(
            sample_monster, "monster", "test_user"
        )

        assert result.is_compliant is False
        assert len(result.issues) > 0

    def test_verify_data_compliance_spell_valid(
        self, compliance_service, sample_spell_compliance, sample_data_source
    ):
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
            srd_compliance=sample_spell_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        result = compliance_service.verify_data_compliance(spell, "spell", "test_user")

        assert result.is_compliant is True
        assert len(result.issues) == 0

    def test_verify_data_compliance_weapon_valid(
        self, compliance_service, sample_weapon_compliance, sample_data_source
    ):
        """Test compliance verification for a valid weapon."""
        weapon = Weapon(
            weapon_name="Test Weapon",
            category="Simple Melee Weapons",
            cost="2 gp",
            damage="1d8 piercing",
            weight="3 lb.",
            properties=["Finesse", "Thrown (range 20/60)"],
            description="A test weapon for unit testing",
            srd_compliance=sample_weapon_compliance,
            data_source=sample_data_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        result = compliance_service.verify_data_compliance(
            weapon, "weapon", "test_user"
        )

        assert result.is_compliant is True
        assert len(result.issues) == 0

    def test_verify_data_compliance_invalid_type(
        self, compliance_service, sample_monster
    ):
        """Test compliance verification with invalid data type."""
        with pytest.raises(ValueError, match="Unsupported data type"):
            compliance_service.verify_data_compliance(
                sample_monster, "invalid_type", "test_user"
            )

    def test_generate_compliance_report(self, compliance_service, sample_monster):
        """Test compliance report generation."""
        report = compliance_service.generate_compliance_report()

        assert isinstance(report, dict)
        assert "report_generated" in report
        assert "audit_statistics" in report
        assert "issues_by_type" in report
        assert "compliance_rules" in report
        assert "official_sources" in report

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

    def test_validate_data_source_unofficial(
        self, compliance_service, sample_data_source
    ):
        """Test data source validation with unofficial source."""
        sample_data_source.is_official = False
        sample_data_source.source_name = "Homebrew Content"

        issues = compliance_service._validate_data_source(sample_data_source)

        assert len(issues) > 0
        assert any("official" in issue.lower() for issue in issues)

    def test_calculate_compliance_hash(self, compliance_service, sample_monster):
        """Test compliance hash calculation."""
        hash_value = compliance_service._calculate_verification_hash(
            sample_monster, "monster"
        )

        assert isinstance(hash_value, str)
        assert len(hash_value) > 0

        # Hash should be consistent
        hash_value2 = compliance_service._calculate_verification_hash(
            sample_monster, "monster"
        )
        assert hash_value == hash_value2

    def test_update_audit_trail(self, compliance_service, sample_compliance):
        """Test audit trail updates."""
        original_length = len(sample_compliance.audit_trail)

        updated_compliance = compliance_service._update_audit_trail(
            sample_compliance, "test_action", "test_user"
        )

        assert len(updated_compliance.audit_trail) == original_length + 1
        assert updated_compliance.audit_trail[-1]["action"] == "test_action"
        assert updated_compliance.audit_trail[-1]["user"] == "test_user"

    @patch("packages.backend.components.srd_compliance_service.datetime")
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
        assert "database_connected" in health
        assert "audit_entries" in health
        assert "data_sources" in health


class TestComplianceResult:
    """Test cases for ComplianceResult model."""

    def test_compliance_result_creation(self):
        """Test ComplianceResult creation."""
        issues = ["Issue 1", "Issue 2"]
        result = ComplianceResult(
            is_compliant=False, issues=issues, timestamp=datetime.utcnow()
        )

        assert result.is_compliant is False
        assert result.issues == issues
        assert result.timestamp is not None

    def test_compliance_result_defaults(self):
        """Test ComplianceResult default values."""
        result = ComplianceResult(is_compliant=True)

        assert result.is_compliant is True
        assert result.issues == []
        assert result.timestamp is not None


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
