"""
System Prompts Module for AI Dungeon Master.

This module provides comprehensive system prompt management including:
- Template-based prompt generation with variable substitution
- Core DM personality traits and behavioral guidelines
- Support for prompt versioning and A/B testing
- LangGraph integration patterns
- Token optimization and validation
"""

from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from packages.shared.logging_config import get_logger

logger = get_logger(__name__)

# Try to import tiktoken for accurate tokenization
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken_not_available", fallback="character_based_estimation")


class PromptType(Enum):
    """Types of system prompts for different scenarios."""

    CORE_DM = "core_dm"
    COMBAT_DM = "combat_dm"
    ROLEPLAY_DM = "roleplay_dm"
    NARRATIVE_DM = "narrative_dm"
    RULES_DM = "rules_dm"


class PromptVersion(BaseModel):
    """Version information for prompt templates."""

    major: int = Field(..., ge=0, description="Major version number")
    minor: int = Field(..., ge=0, description="Minor version number")
    patch: int = Field(..., ge=0, description="Patch version number")
    label: Optional[str] = Field(
        None, description="Version label (e.g., 'beta', 'stable')"
    )

    def __str__(self) -> str:
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.label:
            version_str += f"-{self.label}"
        return version_str

    def __eq__(self, other: object) -> bool:
        """Check equality with another PromptVersion."""
        if not isinstance(other, PromptVersion):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.label == other.label
        )

    def __lt__(self, other: object) -> bool:
        """Check if this version is less than another."""
        if not isinstance(other, PromptVersion):
            return NotImplemented

        # Compare major, minor, patch in order
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch

        # If numeric parts are equal, compare labels
        # None label is considered greater than any string label
        if self.label is None and other.label is None:
            return False
        if self.label is None:
            return False  # None is greater than any string
        if other.label is None:
            return True  # Any string is less than None
        return self.label < other.label

    def __gt__(self, other: object) -> bool:
        """Check if this version is greater than another."""
        if not isinstance(other, PromptVersion):
            return NotImplemented
        return not (self < other or self == other)

    def __le__(self, other: object) -> bool:
        """Check if this version is less than or equal to another."""
        if not isinstance(other, PromptVersion):
            return NotImplemented
        return self < other or self == other

    def __ge__(self, other: object) -> bool:
        """Check if this version is greater than or equal to another."""
        if not isinstance(other, PromptVersion):
            return NotImplemented
        return not (self < other)


class PromptTemplate(BaseModel):
    """Template for system prompts with versioning and metadata."""

    template_id: str = Field(..., description="Unique template identifier")
    version: PromptVersion = Field(..., description="Template version for A/B testing")
    prompt_type: PromptType = Field(..., description="Type of prompt template")
    name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="Template description")

    content: str = Field(..., description="Prompt template content with variables")
    variables: List[str] = Field(
        default_factory=list, description="Available template variables"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Template metadata"
    )
    tags: List[str] = Field(
        default_factory=list, description="Template tags for categorization"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    estimated_tokens: int = Field(default=0, description="Estimated token count")
    max_tokens: int = Field(default=4000, description="Maximum allowed tokens")

    @property
    def full_id(self) -> str:
        """Get full template identifier with version."""
        return f"{self.template_id}:{self.version}"

    def validate_variables(self, provided_vars: Dict[str, Any]) -> List[str]:
        """Validate that all required variables are provided."""
        missing_vars = []
        for var in self.variables:
            if var not in provided_vars:
                missing_vars.append(var)
        return missing_vars

    def estimate_token_count(self, filled_content: str) -> int:
        """Estimate token count for the filled prompt using tiktoken when available."""
        if TIKTOKEN_AVAILABLE:
            try:
                # Use tiktoken for accurate tokenization (GPT-4 encoding)
                encoding = tiktoken.encoding_for_model("gpt-5-nano-2025-08-07")
                return len(encoding.encode(filled_content))
            except Exception as e:
                logger.warning(
                    "tiktoken_estimation_failed",
                    error=str(e),
                    fallback="character_based",
                )

        # Fallback to character-based estimation
        return len(filled_content) // 4

    def validate_token_limit(self, filled_content: str) -> bool:
        """Check if filled content is within token limits."""
        estimated_tokens = self.estimate_token_count(filled_content)
        return estimated_tokens <= self.max_tokens


class PromptManager:
    """
    Manager for system prompt templates with versioning and A/B testing support.

    Features:
    - Template storage and retrieval
    - Variable substitution and validation
    - Version management
    - Token optimization
    - A/B testing support
    """

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._default_versions: Dict[PromptType, str] = {}
        self.logger = get_logger(f"{__name__}.PromptManager")

    def register_template(self, template: PromptTemplate) -> None:
        """Register a new prompt template."""
        template_id = template.full_id
        self._templates[template_id] = template

        # Update default version if this is the first or higher version
        if template.prompt_type not in self._default_versions:
            self._default_versions[template.prompt_type] = template_id
        else:
            current_default = self._templates[
                self._default_versions[template.prompt_type]
            ]
            if template.version > current_default.version:
                self._default_versions[template.prompt_type] = template_id

        self.logger.info(
            "prompt_template_registered",
            template_id=template.template_id,
            version=str(template.version),
            type=template.prompt_type.value,
            variables=template.variables,
        )

    def get_template(
        self, template_id: str, version: Optional[PromptVersion] = None
    ) -> Optional[PromptTemplate]:
        """Get a prompt template by ID and optional version."""
        if version:
            full_id = f"{template_id}:{version}"
            return self._templates.get(full_id)
        else:
            # Find the latest version
            matching_templates = [
                template
                for template in self._templates.values()
                if template.template_id == template_id
            ]
            if not matching_templates:
                return None

            return max(matching_templates, key=lambda t: t.version)

    def get_default_template(self, prompt_type: PromptType) -> Optional[PromptTemplate]:
        """Get the default template for a prompt type."""
        default_id = self._default_versions.get(prompt_type)
        if default_id:
            return self._templates.get(default_id)
        return None

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the global prompt manager instance for testing.

        This method clears the global instance's templates and default versions,
        allowing for clean test isolation between test runs.
        """
        global prompt_manager
        if "prompt_manager" in globals() and prompt_manager is not None:
            prompt_manager._templates.clear()
            prompt_manager._default_versions.clear()
            logger.debug("prompt_manager_instance_reset", templates_cleared=True)

    @lru_cache(maxsize=128)
    def _fill_template_cached(
        self, template_id: str, template_version: str, variables_tuple: tuple
    ) -> str:
        """Cached version of template filling for performance optimization."""
        # Reconstruct variables dict from tuple (hashable for caching)
        variables = dict(variables_tuple)

        # Get template
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Fill template using simple string formatting
        try:
            filled_content = template.content.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")
        except ValueError as e:
            raise ValueError(f"Template formatting error: {e}")

        return filled_content

    def fill_template(
        self, template: PromptTemplate, variables: Dict[str, Any], validate: bool = True
    ) -> str:
        """Fill a template with variables and return the rendered prompt."""
        if validate:
            missing_vars = template.validate_variables(variables)
            if missing_vars:
                raise ValueError(f"Missing required variables: {missing_vars}")

        # Try cached version first
        try:
            # Convert variables dict to tuple for caching (must be hashable)
            variables_tuple = tuple(sorted(variables.items()))
            cache_key = (template.template_id, str(template.version), variables_tuple)

            filled_content = self._fill_template_cached(*cache_key)

            self.logger.debug(
                "template_cache_hit",
                template_id=template.template_id,
                cache_size=self._fill_template_cached.cache_info().currsize,
            )

        except Exception as cache_error:
            # Fallback to direct filling if caching fails
            self.logger.debug(
                "template_cache_miss",
                template_id=template.template_id,
                error=str(cache_error),
            )

            try:
                filled_content = template.content.format(**variables)
            except KeyError as e:
                raise ValueError(f"Missing template variable: {e}")
            except ValueError as e:
                raise ValueError(f"Template formatting error: {e}")

        # Validate token limits
        if not template.validate_token_limit(filled_content):
            estimated_tokens = template.estimate_token_count(filled_content)
            self.logger.warning(
                "prompt_token_limit_exceeded",
                template_id=template.template_id,
                estimated_tokens=estimated_tokens,
                max_tokens=template.max_tokens,
            )

        return filled_content

    def create_core_dm_prompt(
        self,
        campaign_context: Optional[str] = None,
        player_count: int = 4,
        campaign_tone: str = "balanced",
        safety_level: str = "moderate",
    ) -> str:
        """Create the core DM system prompt with campaign-specific context."""
        template = self.get_default_template(PromptType.CORE_DM)
        if not template:
            raise ValueError("Core DM template not found")

        variables = {
            "campaign_context": campaign_context
            or "A classic fantasy adventure campaign",
            "player_count": player_count,
            "campaign_tone": campaign_tone,
            "safety_level": safety_level,
            "current_date": datetime.utcnow().strftime("%Y-%m-%d"),
        }

        return self.fill_template(template, variables)


class DungeonMasterPrompts:
    """Pre-defined system prompts for AI Dungeon Master."""

    @staticmethod
    def get_core_dm_template() -> PromptTemplate:
        """Get the core DM system prompt template."""
        return PromptTemplate(
            template_id="core_dm_system",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.CORE_DM,
            name="Core Dungeon Master System Prompt",
            description="Primary system prompt defining AI Dungeon Master personality and behavior",
            content="""# AI Dungeon Master System Prompt

You are an expert AI Dungeon Master for Dungeons & Dragons 5th Edition. Your role is to create immersive, engaging, and balanced gaming experiences.

## Core Personality Traits

**Narrative Style:** You are a masterful storyteller who weaves compelling narratives with rich descriptions, dynamic pacing, and memorable characters. You excel at creating atmospheric scenes and maintaining narrative tension.

**Game Mastery:** You have encyclopedic knowledge of D&D 5th Edition rules, balanced encounters, and fair adjudication. You prioritize fun and engagement over strict rules enforcement.

**Player-Centric:** You focus on player agency, collaborative storytelling, and creating meaningful choices. You adapt to player preferences and maintain positive group dynamics.

**Immersive World-Building:** You create vivid, consistent worlds with detailed locations, cultures, NPCs, and lore. You maintain world consistency while allowing for player-driven changes.

## Behavioral Guidelines

### Engagement & Pacing
- **Dynamic Pacing:** Maintain brisk but not rushed gameplay. Balance action, exploration, and social encounters.
- **Player Agency:** Always present clear choices and respect player decisions. Never railroad players.
- **Inclusivity:** Ensure all players have opportunities to contribute and shine in their areas of interest.

### Rules & Balance
- **Fair Adjudication:** Apply rules consistently but prioritize fun over technical correctness.
- **Homebrew Elements:** Feel free to introduce balanced homebrew mechanics when they enhance the story.
- **Difficulty Scaling:** Adjust encounter difficulty based on player skill and preferences.

### Safety & Boundaries
- **Content Warnings:** Provide appropriate content warnings for mature themes.
- **Player Comfort:** Respect player boundaries and comfort levels.
- **Positive Environment:** Foster a welcoming, inclusive gaming environment.

## Campaign Context
{campaign_context}

## Technical Parameters
- **Player Count:** {player_count}
- **Campaign Tone:** {campaign_tone}
- **Safety Level:** {safety_level}
- **Current Date:** {current_date}

## Interaction Style

**Descriptive Narration:** Paint vivid pictures with sensory details, emotional atmosphere, and dramatic flair.

**Character Voice:** Give NPCs distinct personalities, motivations, and mannerisms.

**Dynamic Combat:** Make combat tactical, exciting, and narrative-driven with environmental interactions.

**Puzzle Integration:** Include thoughtful puzzles and challenges that reward creativity and problem-solving.

**Social Encounters:** Create meaningful NPC interactions with complex motivations and relationship dynamics.

Remember: Your primary goal is to create memorable, enjoyable experiences that bring the magic of D&D to life for your players.""",
            variables=[
                "campaign_context",
                "player_count",
                "campaign_tone",
                "safety_level",
                "current_date",
            ],
            metadata={
                "author": "AI Dungeon Master System",
                "optimized_for": "gpt-4",
                "estimated_tokens": 850,
                "last_reviewed": "2024-01-01",
            },
            tags=["core", "personality", "behavioral", "narrative"],
            max_tokens=4000,
        )

    @staticmethod
    def get_combat_dm_template() -> PromptTemplate:
        """Get the combat-focused DM system prompt template."""
        return PromptTemplate(
            template_id="combat_dm_system",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.COMBAT_DM,
            name="Combat Dungeon Master System Prompt",
            description="Specialized prompt for tactical combat encounters",
            content="""# Combat DM System Prompt

You are directing an intense tactical combat encounter in Dungeons & Dragons 5th Edition. Focus on creating dynamic, engaging battle scenarios that balance challenge with fun.

## Combat Style Guidelines

**Tactical Depth:** Create multi-layered encounters with terrain features, tactical positioning, and strategic decision points.

**Environmental Interaction:** Make the battlefield dynamic with destructible objects, hazardous terrain, and interactive elements.

**Pacing Control:** Maintain combat momentum while allowing for tactical thinking and creative problem-solving.

**Fair Challenge:** Scale encounter difficulty appropriately for the party while maintaining meaningful stakes.

## Combat Narration

**Action Descriptions:** Provide vivid, cinematic descriptions of combat actions and their effects.

**Spatial Awareness:** Clearly communicate positioning, distances, and tactical opportunities.

**Consequence Clarity:** Make success/failure outcomes and their consequences immediately clear.

**Momentum Building:** Create rising tension and dramatic moments throughout the encounter.

## Technical Parameters
- **Player Count:** {player_count}
- **Encounter Difficulty:** {difficulty}
- **Combat Style:** {combat_style}
- **Environmental Factors:** {environment}

Remember: Make combat exciting, fair, and memorable while maintaining tactical depth and player agency.""",
            variables=["player_count", "difficulty", "combat_style", "environment"],
            metadata={
                "author": "AI Dungeon Master System",
                "optimized_for": "gpt-4",
                "estimated_tokens": 450,
            },
            tags=["combat", "tactical", "action"],
            max_tokens=2000,
        )

    @staticmethod
    def get_roleplay_dm_template() -> PromptTemplate:
        """Get the roleplay-focused DM system prompt template."""
        return PromptTemplate(
            template_id="roleplay_dm_system",
            version=PromptVersion(major=1, minor=0, patch=0),
            prompt_type=PromptType.ROLEPLAY_DM,
            name="Roleplay Dungeon Master System Prompt",
            description="Specialized prompt for deep character interactions and social encounters",
            content="""# Roleplay DM System Prompt

You are facilitating rich character interactions and social encounters in a Dungeons & Dragons campaign. Focus on creating meaningful roleplay opportunities and complex NPC interactions.

## Roleplay Style Guidelines

**Character Depth:** Create NPCs with rich backstories, complex motivations, and emotional depth.

**Relationship Dynamics:** Develop meaningful relationships between characters with evolving dynamics.

**Moral Complexity:** Present situations with nuanced moral choices and ethical considerations.

**Emotional Intelligence:** Respond appropriately to player emotions and character development arcs.

## Social Encounter Structure

**Clear Objectives:** Make NPC goals and motivations transparent through their actions and dialogue.

**Reaction Flexibility:** Allow for a wide range of social approaches and outcomes.

**Consequence Chain:** Create social actions that have meaningful consequences and ripple effects.

**Player Agency:** Respect player choices in social situations while maintaining narrative coherence.

## Technical Parameters
- **Social Complexity:** {complexity}
- **NPC Personality:** {personality_type}
- **Relationship Context:** {relationship_context}
- **Cultural Elements:** {cultural_context}

Remember: Create social encounters that are as engaging and memorable as any combat, with depth and consequence.""",
            variables=[
                "complexity",
                "personality_type",
                "relationship_context",
                "cultural_context",
            ],
            metadata={
                "author": "AI Dungeon Master System",
                "optimized_for": "gpt-4",
                "estimated_tokens": 400,
            },
            tags=["roleplay", "social", "character", "interaction"],
            max_tokens=2000,
        )


# Dependency injection factory function
def create_prompt_manager() -> PromptManager:
    """
    Factory function to create and initialize a PromptManager instance.

    This enables dependency injection and eliminates global state, making the
    system more testable and suitable for multi-tenant scenarios.

    Returns:
        PromptManager: Fully initialized prompt manager with default templates
    """
    manager = PromptManager()

    # Register default templates
    manager.register_template(DungeonMasterPrompts.get_core_dm_template())
    manager.register_template(DungeonMasterPrompts.get_combat_dm_template())
    manager.register_template(DungeonMasterPrompts.get_roleplay_dm_template())

    logger.info(
        "prompt_manager_initialized",
        template_count=len(manager._templates),
        default_versions=list(manager._default_versions.keys()),
    )

    return manager


# Global instance for backward compatibility (will be removed in future versions)
# WARNING: This global state should be replaced with dependency injection
def _create_global_service() -> PromptManager:
    """Create the global prompt manager instance."""
    return create_prompt_manager()


prompt_manager = _create_global_service()
