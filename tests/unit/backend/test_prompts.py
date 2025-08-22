"""
Unit tests for the system prompts module.

Tests cover:
- Prompt template loading and registration
- Template filling and variable substitution
- Version management and A/B testing
- Token limit validation
- Prompt manager functionality
"""

import pytest

from packages.backend.agents.prompts import (
    DungeonMasterPrompts,
    PromptManager,
    PromptTemplate,
    PromptType,
    PromptVersion,
    prompt_manager,
)


class TestPromptVersion:
    """Test the PromptVersion class."""

    def test_version_creation(self):
        """Test creating a version object."""
        version = PromptVersion(major=1, minor=2, patch=3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.label is None

    def test_version_with_label(self):
        """Test version with label."""
        version = PromptVersion(major=2, minor=0, patch=0, label="beta")
        assert str(version) == "2.0.0-beta"

    def test_version_string_representation(self):
        """Test string representation of version."""
        version = PromptVersion(major=1, minor=0, patch=5)
        assert str(version) == "1.0.5"

    def test_version_comparison(self):
        """Test version comparison."""
        v1 = PromptVersion(major=1, minor=0, patch=0)
        v2 = PromptVersion(major=1, minor=1, patch=0)
        v3 = PromptVersion(major=2, minor=0, patch=0)

        assert v1 < v2 < v3
        assert v3 > v2 > v1


class TestPromptTemplate:
    """Test the PromptTemplate class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.version = PromptVersion(major=1, minor=0, patch=0)
        self.template = PromptTemplate(
            template_id="test_template",
            version=self.version,
            prompt_type=PromptType.CORE_DM,
            name="Test Template",
            description="A test template",
            content="Hello {name}, welcome to {place}!",
            variables=["name", "place"],
            max_tokens=1000,
        )

    def test_template_creation(self):
        """Test creating a prompt template."""
        assert self.template.template_id == "test_template"
        assert self.template.prompt_type == PromptType.CORE_DM
        assert self.template.name == "Test Template"
        assert self.template.variables == ["name", "place"]
        assert self.template.max_tokens == 1000

    def test_full_id_property(self):
        """Test the full_id property."""
        expected_id = f"test_template:{self.version}"
        assert self.template.full_id == expected_id

    def test_validate_variables_success(self):
        """Test variable validation with all required variables."""
        variables = {"name": "Alice", "place": "Wonderland"}
        missing = self.template.validate_variables(variables)
        assert missing == []

    def test_validate_variables_missing(self):
        """Test variable validation with missing variables."""
        variables = {"name": "Alice"}  # missing "place"
        missing = self.template.validate_variables(variables)
        assert missing == ["place"]

    def test_validate_variables_extra(self):
        """Test variable validation with extra variables (should still work)."""
        variables = {"name": "Alice", "place": "Wonderland", "extra": "value"}
        missing = self.template.validate_variables(variables)
        assert missing == []

    def test_estimate_token_count(self):
        """Test token count estimation."""
        filled_content = "Hello Alice, welcome to Wonderland!"
        estimated_tokens = self.template.estimate_token_count(filled_content)
        assert estimated_tokens == 6  # 30 characters / 4 = 7.5, floored to 6

    def test_validate_token_limit_under_limit(self):
        """Test token limit validation when under limit."""
        filled_content = "Short content"
        assert self.template.validate_token_limit(filled_content) is True

    def test_validate_token_limit_over_limit(self):
        """Test token limit validation when over limit."""
        long_content = "x" * 4001  # This will exceed 1000 token limit
        assert self.template.validate_token_limit(long_content) is False


class TestPromptManager:
    """Test the PromptManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = PromptManager()
        self.template = PromptTemplate(
            template_id="test_template",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Test Template",
            description="A test template",
            content="Hello {name}!",
            variables=["name"],
            max_tokens=1000,
        )

    def test_register_template(self):
        """Test registering a template."""
        self.manager.register_template(self.template)

        full_id = self.template.full_id
        assert full_id in self.manager._templates
        assert self.manager._templates[full_id] is self.template

    def test_register_template_updates_default(self):
        """Test that registering a template updates default version."""
        self.manager.register_template(self.template)

        assert (
            self.manager._default_versions[PromptType.CORE_DM] == self.template.full_id
        )

    def test_register_higher_version_becomes_default(self):
        """Test that a higher version becomes the default."""
        # Register lower version first
        v1 = PromptTemplate(
            template_id="test_template",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Test Template v1",
            description="Version 1",
            content="Hello {name}!",
            variables=["name"],
        )

        # Register higher version
        v2 = PromptTemplate(
            template_id="test_template",
            version=PromptVersion(major=1, minor=1, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Test Template v2",
            description="Version 2",
            content="Hi {name}!",
            variables=["name"],
        )

        self.manager.register_template(v1)
        assert self.manager._default_versions[PromptType.CORE_DM] == v1.full_id

        self.manager.register_template(v2)
        assert self.manager._default_versions[PromptType.CORE_DM] == v2.full_id

    def test_get_template_with_version(self):
        """Test getting a template with specific version."""
        self.manager.register_template(self.template)

        retrieved = self.manager.get_template("test_template", self.template.version)
        assert retrieved is self.template

    def test_get_template_latest_version(self):
        """Test getting the latest version of a template."""
        v1 = PromptTemplate(
            template_id="test_template",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Test Template v1",
            content="Hello {name}!",
            variables=["name"],
        )

        v2 = PromptTemplate(
            template_id="test_template",
            version=PromptVersion(major=1, minor=1, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Test Template v2",
            content="Hi {name}!",
            variables=["name"],
        )

        self.manager.register_template(v1)
        self.manager.register_template(v2)

        retrieved = self.manager.get_template("test_template")
        assert retrieved is v2  # Should get the latest version

    def test_get_template_not_found(self):
        """Test getting a non-existent template."""
        retrieved = self.manager.get_template("non_existent")
        assert retrieved is None

    def test_get_default_template(self):
        """Test getting the default template for a prompt type."""
        self.manager.register_template(self.template)

        default = self.manager.get_default_template(PromptType.CORE_DM)
        assert default is self.template

    def test_get_default_template_not_found(self):
        """Test getting default template when none exists."""
        default = self.manager.get_default_template(PromptType.COMBAT_DM)
        assert default is None

    def test_fill_template_success(self):
        """Test successfully filling a template."""
        self.manager.register_template(self.template)

        variables = {"name": "Alice"}
        filled = self.manager.fill_template(self.template, variables)

        assert filled == "Hello Alice!"

    def test_fill_template_missing_variables(self):
        """Test filling template with missing variables."""
        self.manager.register_template(self.template)

        variables = {}  # Missing "name"

        with pytest.raises(ValueError, match="Missing required variables"):
            self.manager.fill_template(self.template, variables)

    def test_fill_template_invalid_format(self):
        """Test filling template with invalid format string."""
        template = PromptTemplate(
            template_id="bad_template",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Bad Template",
            content="Hello {name",  # Missing closing brace
            variables=["name"],
        )
        self.manager.register_template(template)

        variables = {"name": "Alice"}

        with pytest.raises(ValueError, match="Template formatting error"):
            self.manager.fill_template(template, variables)

    def test_create_core_dm_prompt(self):
        """Test creating a core DM prompt."""
        core_template = DungeonMasterPrompts.get_core_dm_template()
        self.manager.register_template(core_template)

        prompt = self.manager.create_core_dm_prompt(
            campaign_context="A dark fantasy campaign",
            player_count=3,
            campaign_tone="dark",
        )

        assert "A dark fantasy campaign" in prompt
        assert "3" in prompt
        assert "dark" in prompt

    def test_create_core_dm_prompt_no_template(self):
        """Test creating core DM prompt when template doesn't exist."""
        with pytest.raises(ValueError, match="Core DM template not found"):
            self.manager.create_core_dm_prompt()


class TestDungeonMasterPrompts:
    """Test the DungeonMasterPrompts static methods."""

    def test_get_core_dm_template(self):
        """Test getting the core DM template."""
        template = DungeonMasterPrompts.get_core_dm_template()

        assert template.template_id == "core_dm_system"
        assert template.prompt_type == PromptType.CORE_DM
        assert template.name == "Core Dungeon Master System Prompt"
        assert "campaign_context" in template.variables
        assert "player_count" in template.variables
        assert template.max_tokens == 4000

    def test_get_combat_dm_template(self):
        """Test getting the combat DM template."""
        template = DungeonMasterPrompts.get_combat_dm_template()

        assert template.template_id == "combat_dm_system"
        assert template.prompt_type == PromptType.COMBAT_DM
        assert template.name == "Combat Dungeon Master System Prompt"
        assert "player_count" in template.variables
        assert "difficulty" in template.variables

    def test_get_roleplay_dm_template(self):
        """Test getting the roleplay DM template."""
        template = DungeonMasterPrompts.get_roleplay_dm_template()

        assert template.template_id == "roleplay_dm_system"
        assert template.prompt_type == PromptType.ROLEPLAY_DM
        assert template.name == "Roleplay Dungeon Master System Prompt"
        assert "complexity" in template.variables
        assert "personality_type" in template.variables


class TestGlobalPromptManager:
    """Test the global prompt manager instance."""

    def test_global_manager_exists(self):
        """Test that the global prompt manager exists."""
        assert prompt_manager is not None
        assert isinstance(prompt_manager, PromptManager)

    def test_global_manager_has_templates(self):
        """Test that the global manager has default templates registered."""
        # Should have at least the core templates
        assert len(prompt_manager._templates) >= 3  # core, combat, roleplay

        # Should have default versions set
        assert PromptType.CORE_DM in prompt_manager._default_versions
        assert PromptType.COMBAT_DM in prompt_manager._default_versions
        assert PromptType.ROLEPLAY_DM in prompt_manager._default_versions

    def test_global_manager_can_create_prompt(self):
        """Test that the global manager can create a core DM prompt."""
        prompt = prompt_manager.create_core_dm_prompt(
            campaign_context="Test campaign", player_count=4, campaign_tone="heroic"
        )

        assert "Test campaign" in prompt
        assert "4" in prompt
        assert "heroic" in prompt
