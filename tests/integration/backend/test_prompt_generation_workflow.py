"""
Integration tests for end-to-end prompt generation workflow.

These tests verify the complete prompt generation pipeline including:
- Template loading and registration
- Variable substitution and validation
- Token estimation with tiktoken
- Template caching functionality
- Error handling and edge cases
- Performance characteristics
"""

import pytest
from unittest.mock import Mock, patch

from packages.backend.agents.prompts import (
    PromptManager,
    PromptTemplate,
    PromptVersion,
    PromptType,
    DungeonMasterPrompts,
    create_prompt_manager,
    TIKTOKEN_AVAILABLE,
)


class TestPromptGenerationWorkflowIntegration:
    """Integration tests for the complete prompt generation workflow."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Reset any global state
        PromptManager.reset_instance()

    def teardown_method(self):
        """Clean up after each test."""
        PromptManager.reset_instance()

    def test_complete_prompt_generation_workflow(self):
        """Test the complete workflow from template creation to prompt generation."""
        # Create a new prompt manager instance
        manager = create_prompt_manager()

        # Verify templates are registered
        assert len(manager._templates) == 3
        assert len(manager._default_versions) == 3

        # Get a template
        core_template = manager.get_default_template(PromptType.CORE_DM)
        assert core_template is not None
        assert core_template.prompt_type == PromptType.CORE_DM

        # Test template filling with variables
        variables = {
            "campaign_context": "A dark fantasy campaign in the Forgotten Realms",
            "player_count": 4,
            "campaign_tone": "dark and mysterious",
            "safety_level": "moderate",
            "current_date": "2024-08-23",
        }

        filled_prompt = manager.fill_template(core_template, variables)

        # Verify the prompt was filled correctly
        assert "Forgotten Realms" in filled_prompt
        assert "dark and mysterious" in filled_prompt
        assert "4" in filled_prompt
        assert "2024-08-23" in filled_prompt
        assert "AI Dungeon Master" in filled_prompt

        # Verify token estimation works
        estimated_tokens = core_template.estimate_token_count(filled_prompt)
        assert isinstance(estimated_tokens, int)
        assert estimated_tokens > 0

    def test_template_caching_functionality(self):
        """Test that template caching works correctly for performance."""
        manager = create_prompt_manager()
        template = manager.get_default_template(PromptType.CORE_DM)

        variables = {
            "campaign_context": "Test campaign",
            "player_count": 3,
            "campaign_tone": "epic",
            "safety_level": "high",
            "current_date": "2024-08-23",
        }

        # Fill template multiple times with same variables
        prompt1 = manager.fill_template(template, variables)
        prompt2 = manager.fill_template(template, variables)

        # Should get the same result
        assert prompt1 == prompt2

        # Check cache info if available
        if hasattr(manager, "_fill_template_cached"):
            cache_info = manager._fill_template_cached.cache_info()
            assert cache_info.hits >= 1  # At least one cache hit
            assert cache_info.misses >= 1  # At least one cache miss

    def test_token_estimation_accuracy(self):
        """Test token estimation accuracy with and without tiktoken."""
        manager = create_prompt_manager()
        template = manager.get_default_template(PromptType.CORE_DM)

        test_text = "This is a test prompt for token estimation accuracy."

        estimated_tokens = template.estimate_token_count(test_text)
        character_based = len(test_text) // 4

        if TIKTOKEN_AVAILABLE:
            # Should use tiktoken estimation
            assert estimated_tokens > 0
            # tiktoken should be more accurate than character-based
            assert abs(estimated_tokens - character_based) <= character_based * 0.5
        else:
            # Should fall back to character-based estimation
            assert estimated_tokens == character_based

    def test_prompt_validation_and_error_handling(self):
        """Test prompt validation and error handling throughout the workflow."""
        manager = create_prompt_manager()
        template = manager.get_default_template(PromptType.CORE_DM)

        # Test missing variables
        incomplete_variables = {
            "campaign_context": "Test campaign",
            # Missing other required variables
        }

        with pytest.raises(ValueError, match="Missing required variables"):
            manager.fill_template(template, incomplete_variables)

        # Test invalid template variables
        with pytest.raises(ValueError, match="Template formatting error"):
            # Create a template with invalid format string to trigger formatting error
            invalid_template = PromptTemplate(
                template_id="invalid_template",
                version=PromptVersion(major=1, minor=0, patch=0),
                prompt_type=PromptType.CORE_DM,
                name="Invalid Template",
                description="Template with invalid format string",
                content="Template with {invalid:format}",
                variables=["invalid"],
                max_tokens=1000,
            )
            invalid_variables = {"invalid": "test"}
            manager.fill_template(invalid_template, invalid_variables)

    def test_template_version_management(self):
        """Test template version management and A/B testing capabilities."""
        manager = PromptManager()

        # Register multiple versions of the same template
        template_v1 = PromptTemplate(
            template_id="test_template",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Test Template V1",
            description="First version of test template",
            content="Version {version} content for {context}",
            variables=["version", "context"],
            max_tokens=1000,
        )

        template_v2 = PromptTemplate(
            template_id="test_template",
            version=PromptVersion(major=1, minor=1, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Test Template V2",
            description="Second version of test template",
            content="Updated version {version} content for {context} with improvements",
            variables=["version", "context"],
            max_tokens=1000,
        )

        manager.register_template(template_v1)
        manager.register_template(template_v2)

        # Should default to highest version
        default_template = manager.get_default_template(PromptType.CORE_DM)
        assert default_template.version == PromptVersion(major=1, minor=1, patch=0)

        # Can retrieve specific versions
        specific_template = manager.get_template(
            "test_template", PromptVersion(major=1, minor=0, patch=0)
        )
        assert specific_template.version == PromptVersion(major=1, minor=0, patch=0)

    def test_dependency_injection_pattern(self):
        """Test that the dependency injection pattern works correctly."""
        # Test creating multiple instances
        manager1 = create_prompt_manager()
        manager2 = create_prompt_manager()

        # Should be different instances
        assert manager1 is not manager2

        # But both should have the same templates
        assert len(manager1._templates) == len(manager2._templates) == 3

        # Test with custom template registration
        custom_manager = PromptManager()
        custom_template = PromptTemplate(
            template_id="custom_template",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Custom Template",
            description="Custom template for testing",
            content="Custom prompt: {message}",
            variables=["message"],
            max_tokens=500,
        )

        custom_manager.register_template(custom_template)

        # Should have only the custom template
        assert len(custom_manager._templates) == 1
        assert custom_manager.get_template("custom_template") is not None

    def test_performance_characteristics(self):
        """Test performance characteristics of the prompt generation system."""
        import time

        manager = create_prompt_manager()
        template = manager.get_default_template(PromptType.CORE_DM)

        variables = {
            "campaign_context": "Performance test campaign",
            "player_count": 4,
            "campaign_tone": "balanced",
            "safety_level": "moderate",
            "current_date": "2024-08-23",
        }

        # Measure time for multiple fills
        start_time = time.time()

        for i in range(100):
            variables["player_count"] = i % 6 + 1  # Vary slightly to avoid pure caching
            filled_prompt = manager.fill_template(template, variables)
            assert len(filled_prompt) > 100  # Basic validation

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete within reasonable time (adjust based on actual performance)
        assert total_time < 5.0  # 5 seconds max for 100 operations

        # Average time per operation should be reasonable
        avg_time_per_operation = total_time / 100
        assert avg_time_per_operation < 0.05  # 50ms max per operation

    def test_error_recovery_and_resilience(self):
        """Test error recovery and system resilience."""
        manager = create_prompt_manager()

        # Test with corrupted template (simulate database corruption)
        with patch.object(manager, "_templates", {}):
            template = manager.get_default_template(PromptType.CORE_DM)
            assert template is None  # Should handle gracefully

        # Test with corrupted template structure
        corrupted_template = PromptTemplate(
            template_id="corrupted",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Corrupted Template",
            description="Template with issues",
            content="Template with {undefined_variable} and {missing_var}",
            variables=["defined_var"],  # Missing variables in content
            max_tokens=1000,
        )

        manager.register_template(corrupted_template)

        # Should handle undefined variables gracefully
        with pytest.raises(ValueError):
            manager.fill_template(corrupted_template, {"defined_var": "test"})

    def test_memory_management_with_caching(self):
        """Test memory management aspects of the caching system."""
        manager = create_prompt_manager()
        template = manager.get_default_template(PromptType.CORE_DM)

        # Fill with many different variable combinations
        for i in range(200):  # Exceed cache size
            variables = {
                "campaign_context": f"Campaign {i}",
                "player_count": i % 6 + 1,
                "campaign_tone": "balanced",
                "safety_level": "moderate",
                "current_date": "2024-08-23",
            }
            filled_prompt = manager.fill_template(template, variables)

        # Cache should still be functional
        if hasattr(manager, "_fill_template_cached"):
            cache_info = manager._fill_template_cached.cache_info()
            assert cache_info.currsize <= cache_info.maxsize

    @patch("packages.backend.agents.prompts.TIKTOKEN_AVAILABLE", False)
    def test_fallback_token_estimation(self):
        """Test fallback token estimation when tiktoken is not available."""
        manager = create_prompt_manager()
        template = manager.get_default_template(PromptType.CORE_DM)

        test_text = "This is a test prompt with exactly 40 characters."

        estimated_tokens = template.estimate_token_count(test_text)

        # Should use character-based estimation
        expected_tokens = len(test_text) // 4  # 40 // 4 = 10
        assert estimated_tokens == expected_tokens

    @patch("packages.backend.agents.prompts.TIKTOKEN_AVAILABLE", True)
    @patch("tiktoken.encoding_for_model")
    def test_tiktoken_integration(self, mock_encoding_for_model):
        """Test tiktoken integration when available."""
        # Mock tiktoken encoding
        mock_encoding = Mock()
        mock_encoding.encode.return_value = ["token1", "token2", "token3"]  # 3 tokens
        mock_encoding_for_model.return_value = mock_encoding

        manager = create_prompt_manager()
        template = manager.get_default_template(PromptType.CORE_DM)

        test_text = "Short test prompt"

        estimated_tokens = template.estimate_token_count(test_text)

        # Should use tiktoken estimation
        assert estimated_tokens == 3
        mock_encoding_for_model.assert_called_with("gpt-4")
        mock_encoding.encode.assert_called_with(test_text)
