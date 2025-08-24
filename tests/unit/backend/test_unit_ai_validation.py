"""
Unit tests for AI Validation Service.

Tests cover:
- AI response validation against SRD rules
- Accuracy scoring and issue detection
- Validation metrics and reporting
- Improvement feedback generation
- Error handling and edge cases
- Terminology and rule compliance validation
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from packages.backend.components.ai_validation_service import (
    AIValidationService,
    ValidationMetrics,
    ValidationResult,
)


class TestAIValidationService:
    """Test cases for AI Validation Service."""

    @pytest.fixture
    def validation_service(self):
        """Create a fresh AI Validation Service for each test."""
        service = AIValidationService()
        service.reset_metrics()
        return service

    @pytest.fixture
    def sample_accurate_response(self):
        """Create a sample accurate AI response."""
        return {
            "query": "What is the armor class of a Goblin?",
            "ai_response": "A Goblin has an armor class of 15, hit points of 7 (2d6), and uses a scimitar that deals 1d6+2 slashing damage.",
            "expected_entities": ["Goblin"],
        }

    @pytest.fixture
    def sample_inaccurate_response(self):
        """Create a sample inaccurate AI response."""
        return {
            "query": "What is the armor class of a Goblin?",
            "ai_response": "A Goblin has an armor class of 18, hit points of 15, and uses a longsword that deals 2d8 slashing damage.",
            "expected_entities": ["Goblin"],
        }

    def test_service_initialization(self, validation_service):
        """Test AI Validation Service initialization."""
        assert isinstance(validation_service, AIValidationService)
        assert isinstance(validation_service.metrics, ValidationMetrics)
        assert len(validation_service.validation_rules) > 0
        assert len(validation_service.terminology_rules) > 0

    @pytest.mark.asyncio
    async def test_validate_accurate_response(
        self, validation_service, sample_accurate_response
    ):
        """Test validation of an accurate AI response."""
        with patch(
            "packages.backend.components.ai_validation_service.rules_engine"
        ) as mock_engine:
            # Mock Goblin monster data
            mock_monster = Mock()
            mock_monster.found = True
            mock_monster.data = {
                "monster_name": "Goblin",
                "armor_class": 15,
                "hit_points": "7 (2d6)",
            }
            mock_engine.query_monster = AsyncMock(return_value=mock_monster)

            result = await validation_service.validate_ai_response(
                **sample_accurate_response
            )

            assert isinstance(result, ValidationResult)
            assert result.is_accurate is True
            assert result.accuracy_score > 0.8
            assert len(result.issues_found) == 0

    @pytest.mark.asyncio
    async def test_validate_inaccurate_response(
        self, validation_service, sample_inaccurate_response
    ):
        """Test validation of an inaccurate AI response."""
        with patch(
            "packages.backend.components.ai_validation_service.rules_engine"
        ) as mock_engine:
            # Mock Goblin monster data (different from AI response)
            mock_monster = Mock()
            mock_monster.found = True
            mock_monster.data = {
                "monster_name": "Goblin",
                "armor_class": 15,
                "hit_points": "7 (2d6)",
            }
            mock_engine.query_monster = AsyncMock(return_value=mock_monster)

            result = await validation_service.validate_ai_response(
                **sample_inaccurate_response
            )

            assert isinstance(result, ValidationResult)
            assert result.is_accurate is False
            assert result.accuracy_score < 0.8
            assert len(result.issues_found) > 0

    @pytest.mark.asyncio
    async def test_validate_response_with_terminology_errors(self, validation_service):
        """Test validation of response with terminology errors."""
        validation_data = {
            "query": "How do you calculate hit points?",
            "ai_response": "You calculate health points by rolling dice and adding your constitution modifier.",
            "expected_entities": [],
        }

        result = await validation_service.validate_ai_response(**validation_data)

        assert isinstance(result, ValidationResult)
        assert len(result.issues_found) > 0
        assert any("terminology" in issue.lower() for issue in result.issues_found)

    @pytest.mark.asyncio
    async def test_validate_response_with_rule_errors(self, validation_service):
        """Test validation of response with rule errors."""
        validation_data = {
            "query": "How do critical hits work?",
            "ai_response": "Critical hits occur on a roll of 19-20 and deal double damage including modifiers.",
            "expected_entities": [],
        }

        result = await validation_service.validate_ai_response(**validation_data)

        assert isinstance(result, ValidationResult)
        assert len(result.issues_found) > 0

    def test_extract_mentioned_entities(self, validation_service):
        """Test entity extraction from AI responses."""
        text = "A Goblin has 15 AC and uses a scimitar, while a Fire Bolt spell deals 1d10 fire damage."

        entities = validation_service._extract_mentioned_entities(text)

        assert "goblin" in entities
        assert "fire bolt" in entities
        assert "scimitar" in entities

    def test_extract_monster_stats_from_text(self, validation_service):
        """Test monster statistics extraction from text."""
        text = "The Goblin has armor class 15, hit points 7 (2d6), and challenge rating 1/4."

        stats = validation_service._extract_monster_stats_from_text(text)

        assert stats["armor_class"] == 15
        assert stats["hit_points"] == "7 (2d6)"
        assert stats["challenge_rating"] == "1/4"

    def test_extract_spell_info_from_text(self, validation_service):
        """Test spell information extraction from text."""
        text = "Fire Bolt is a 0th level Evocation spell with casting time of 1 action and range of 120 feet."

        info = validation_service._extract_spell_info_from_text(text)

        assert info["level"] == 0
        assert "1 action" in info["casting_time"]
        assert "120 feet" in info["range"]

    def test_extract_weapon_info_from_text(self, validation_service):
        """Test weapon information extraction from text."""
        text = "The longsword deals 1d8 slashing damage and has the Versatile property."

        info = validation_service._extract_weapon_info_from_text(text)

        assert "1d8 slashing" in info["damage"]
        assert "Versatile" in info["properties"]

    def test_compare_hit_points(self, validation_service):
        """Test hit points comparison."""
        # Same hit points should match
        assert (
            validation_service._compare_hit_points("10 (3d6+1)", "10 (3d6+1)") is True
        )

        # Similar hit points should match (within variance)
        assert validation_service._compare_hit_points("10", "12") is True

        # Very different should not match
        assert validation_service._compare_hit_points("10", "25") is False

    def test_compare_challenge_ratings(self, validation_service):
        """Test challenge rating comparison."""
        assert validation_service._compare_challenge_ratings("1", "1") is True
        assert validation_service._compare_challenge_ratings("1/4", "0.25") is True
        assert validation_service._compare_challenge_ratings("1", "5") is False

    def test_compare_casting_times(self, validation_service):
        """Test casting time comparison."""
        assert validation_service._compare_casting_times("1 action", "1 action") is True
        assert validation_service._compare_casting_times("action", "1 action") is True
        assert (
            validation_service._compare_casting_times("bonus action", "1 bonus action")
            is True
        )

    def test_compare_ranges(self, validation_service):
        """Test range comparison."""
        assert validation_service._compare_ranges("120 feet", "120 feet") is True
        assert validation_service._compare_ranges("30 feet", "30 ft") is True
        assert validation_service._compare_ranges("self", "self") is True

    def test_compare_damage(self, validation_service):
        """Test damage comparison."""
        assert (
            validation_service._compare_damage("1d8 slashing", "1d8 slashing damage")
            is True
        )
        assert validation_service._compare_damage("2d6+3", "2d6 + 3 piercing") is True

    def test_calculate_accuracy_score(self, validation_service):
        """Test accuracy score calculation."""
        # No issues should give perfect score
        score = validation_service._calculate_accuracy_score([], [])
        assert score == 1.0

        # Issues should reduce score
        score = validation_service._calculate_accuracy_score(["Issue 1"], [])
        assert score == 0.7  # 0.8 - 0.1

        # Corrections should reduce score further
        score = validation_service._calculate_accuracy_score(
            ["Issue 1"], ["Correction 1"]
        )
        assert score == 0.65  # 0.8 - 0.1 - 0.05

    def test_update_metrics(self, validation_service):
        """Test metrics update functionality."""
        initial_validations = validation_service.metrics.total_validations

        validation_service._update_metrics("monster", True, 0.9, [])

        assert validation_service.metrics.total_validations == initial_validations + 1
        assert validation_service.metrics.accurate_responses == 1
        assert validation_service.metrics.accuracy_rate == 1.0

    def test_get_validation_metrics(self, validation_service):
        """Test validation metrics retrieval."""
        metrics = validation_service.get_validation_metrics()

        assert isinstance(metrics, dict)
        assert "total_validations" in metrics
        assert "accuracy_rate" in metrics
        assert "average_accuracy_score" in metrics

    def test_generate_improvement_feedback(self, validation_service):
        """Test improvement feedback generation."""
        validation_result = ValidationResult(
            is_accurate=False,
            accuracy_score=0.6,
            issues_found=["Terminology: 'health points' should be 'hit points'"],
            corrections_suggested=["Use proper D&D terminology"],
            validation_details=[],
            validated_at=datetime.utcnow(),
            validation_type="terminology",
        )

        feedback = validation_service.generate_improvement_feedback(validation_result)

        assert isinstance(feedback, dict)
        assert "overall_accuracy" in feedback
        assert "improvement_areas" in feedback
        assert "specific_corrections" in feedback
        assert "terminology" in feedback["improvement_areas"]

    def test_categorize_issues(self, validation_service):
        """Test issue categorization."""
        issues = [
            "Terminology: 'health points' should be 'hit points'",
            "Armor Class mismatch for Goblin: AI said 18, SRD says 15",
            "Missing information: No mention of Goblin's Nimble Escape",
            "Critical hit range incorrect",
        ]

        categories = validation_service._categorize_issues(issues)

        assert "terminology" in categories
        assert "statistics" in categories
        assert "missing_info" in categories
        assert "mechanics" in categories

        assert len(categories["terminology"]) == 1
        assert len(categories["statistics"]) == 1
        assert len(categories["mechanics"]) == 1

    def test_reset_metrics(self, validation_service):
        """Test metrics reset functionality."""
        # Add some metrics
        validation_service._update_metrics("test", True, 0.9, [])

        assert validation_service.metrics.total_validations > 0

        validation_service.reset_metrics()

        assert validation_service.metrics.total_validations == 0
        assert validation_service.metrics.accurate_responses == 0

    def test_health_check(self, validation_service):
        """Test health check functionality."""
        health = validation_service.health_check()

        assert isinstance(health, dict)
        assert "status" in health
        assert "validation_rules_loaded" in health
        assert "terminology_rules_loaded" in health
        assert "metrics" in health

    @pytest.mark.asyncio
    async def test_validate_response_error_handling(self, validation_service):
        """Test error handling in validation."""
        validation_data = {
            "query": "Test query",
            "ai_response": "Test response",
            "expected_entities": ["NonexistentEntity"],
        }

        with patch(
            "packages.backend.components.ai_validation_service.rules_engine"
        ) as mock_engine:
            # Mock engine to raise exception
            mock_engine.query_monster = AsyncMock(
                side_effect=Exception("Database error")
            )

            result = await validation_service.validate_ai_response(**validation_data)

            assert isinstance(result, ValidationResult)
            assert result.is_accurate is False
            assert len(result.issues_found) > 0

    def test_terminology_validation(self, validation_service):
        """Test D&D terminology validation."""
        text = "The monster has 10 health points and 15 defense."

        issues = validation_service._validate_terminology(text)

        assert len(issues) >= 2  # Should catch both "health points" and "defense"
        assert any("hit points" in issue for issue in issues)
        assert any("armor class" in issue for issue in issues)

    def test_rule_compliance_validation(self, validation_service):
        """Test D&D rule compliance validation."""
        text = "Critical hits occur on a roll of 19-20 and deal double damage including all modifiers."

        issues = validation_service._validate_rule_compliance(text)

        assert len(issues) > 0
        assert any("critical hit" in issue.lower() for issue in issues)

    @pytest.mark.asyncio
    async def test_validation_with_empty_response(self, validation_service):
        """Test validation with empty AI response."""
        validation_data = {
            "query": "What is a Goblin?",
            "ai_response": "",
            "expected_entities": ["Goblin"],
        }

        result = await validation_service.validate_ai_response(**validation_data)

        assert isinstance(result, ValidationResult)
        assert result.is_accurate is False
        assert result.accuracy_score < 0.8

    @pytest.mark.asyncio
    async def test_validation_with_none_response(self, validation_service):
        """Test validation with None AI response."""
        validation_data = {
            "query": "What is a Goblin?",
            "ai_response": None,
            "expected_entities": ["Goblin"],
        }

        result = await validation_service.validate_ai_response(**validation_data)

        assert isinstance(result, ValidationResult)
        assert result.is_accurate is False
        assert len(result.issues_found) > 0


class TestValidationResult:
    """Test cases for ValidationResult model."""

    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        issues = ["Issue 1", "Issue 2"]
        corrections = ["Correction 1"]
        details = ["Detail 1"]

        result = ValidationResult(
            is_accurate=False,
            accuracy_score=0.75,
            issues_found=issues,
            corrections_suggested=corrections,
            validation_details=details,
            validated_at=datetime.utcnow(),
            validation_type="test",
        )

        assert result.is_accurate is False
        assert result.accuracy_score == 0.75
        assert result.issues_found == issues
        assert result.corrections_suggested == corrections
        assert result.validation_details == details
        assert result.validation_type == "test"

    def test_validation_result_defaults(self):
        """Test ValidationResult default values."""
        result = ValidationResult()

        assert result.is_accurate is None
        assert result.accuracy_score is None
        assert result.issues_found is None
        assert result.corrections_suggested is None
        assert result.validation_details is None
        assert result.validated_at is None
        assert result.validation_type is None


class TestValidationMetrics:
    """Test cases for ValidationMetrics model."""

    def test_validation_metrics_creation(self):
        """Test ValidationMetrics creation."""
        common_issues = {"terminology": 5, "statistics": 3}
        validation_types = {"monster": 10, "spell": 8}

        metrics = ValidationMetrics(
            total_validations=18,
            accurate_responses=15,
            accuracy_rate=0.833,
            average_accuracy_score=0.85,
            common_issues=common_issues,
            validation_types=validation_types,
        )

        assert metrics.total_validations == 18
        assert metrics.accurate_responses == 15
        assert metrics.accuracy_rate == 0.833
        assert metrics.average_accuracy_score == 0.85
        assert metrics.common_issues == common_issues
        assert metrics.validation_types == validation_types

    def test_validation_metrics_defaults(self):
        """Test ValidationMetrics default values."""
        metrics = ValidationMetrics()

        assert metrics.total_validations == 0
        assert metrics.accurate_responses == 0
        assert metrics.accuracy_rate == 0.0
        assert metrics.average_accuracy_score == 0.0
        assert metrics.common_issues == {}
        assert metrics.validation_types == {}
