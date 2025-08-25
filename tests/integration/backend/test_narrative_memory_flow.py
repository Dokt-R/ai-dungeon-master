"""
Integration tests for end-to-end narrative memory flow.

This module provides comprehensive integration tests for the complete memory system
including DM graph integration, memory context preparation, and memory updates.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.backend.agents.dm_graph import DMGraphService, DMGraphState
from packages.backend.components.memory_service import MemoryService, MemoryContext
from packages.shared.models import MemoryState


class TestNarrativeMemoryFlow:
    """Integration tests for complete narrative memory flow."""

    @pytest.fixture
    def memory_service(self):
        """Create memory service for testing."""
        return MemoryService()

    @pytest.fixture
    def dm_graph_service(self):
        """Create DM graph service for testing."""
        return DMGraphService()

    def setup_method(self):
        """Set up test environment."""
        self.session_id = "test_session_123"
        self.correlation_id = "test_correlation_456"

    @pytest.mark.asyncio
    async def test_memory_context_preparation_integration(self, memory_service):
        """Test memory context preparation with realistic data."""
        # Add some conversation history to memory
        memory_state = await memory_service._load_memory_state(self.session_id)

        # Add user messages
        memory_state.add_message("user", "I want to explore the nearby cave")
        memory_state.add_message(
            "assistant",
            "You approach the dark cave entrance, hearing water dripping from within.",
        )
        memory_state.add_message("user", "I light my torch and go inside")
        memory_state.add_message(
            "assistant",
            "The torch illuminates the cave, revealing beautiful crystal formations along the walls.",
        )

        # Prepare memory context
        user_prompt = "I search for any treasure or valuable items"

        context = await memory_service.prepare_memory_context(
            session_id=self.session_id,
            user_prompt=user_prompt,
            correlation_id=self.correlation_id,
        )

        # Verify context structure
        assert isinstance(context, MemoryContext)
        assert len(context.recent_events) > 0
        assert context.token_count > 0
        assert context.summary is not None

        # Verify recent events include conversation history
        event_contents = [event["content"] for event in context.recent_events]
        assert any("cave" in content.lower() for content in event_contents)
        assert any("torch" in content.lower() for content in event_contents)

        # Verify token count is reasonable
        assert context.token_count < 2000  # Should be within limits

    @pytest.mark.asyncio
    async def test_memory_update_after_interaction(self, memory_service):
        """Test memory update after conversation interaction."""
        # Start with empty memory
        initial_memory = await memory_service._load_memory_state(self.session_id)
        initial_count = len(initial_memory.messages)

        # Simulate user prompt and AI response
        user_prompt = "I attack the goblin with my sword"
        ai_response = "You swing your sword and strike the goblin, dealing 8 damage. The goblin snarls and attacks back!"

        # Update memory after interaction
        await memory_service.update_memory_after_interaction(
            session_id=self.session_id,
            user_prompt=user_prompt,
            ai_response=ai_response,
            correlation_id=self.correlation_id,
        )

        # Verify memory was updated
        updated_memory = await memory_service._load_memory_state(self.session_id)
        assert len(updated_memory.messages) == initial_count + 2

        # Verify messages were added in correct order
        messages = updated_memory.messages[-2:]
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == user_prompt
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == ai_response

    @pytest.mark.asyncio
    async def test_memory_context_with_relevance_scoring(self, memory_service):
        """Test memory context with relevance scoring for related topics."""
        # Add conversation history with various topics
        memory_state = await memory_service._load_memory_state(self.session_id)

        memory_state.add_message("user", "I want to buy some potions from the merchant")
        memory_state.add_message(
            "assistant", "The merchant offers healing potions for 50 gold each."
        )
        memory_state.add_message("user", "I ask about the nearby dungeon")
        memory_state.add_message(
            "assistant",
            "The merchant warns you about the dangerous dungeon to the north.",
        )
        memory_state.add_message("user", "Tell me about the local tavern")
        memory_state.add_message(
            "assistant",
            "The tavern is called The Rusty Dragon and serves excellent ale.",
        )

        # Test relevance with dungeon-related prompt
        dungeon_prompt = "I'm preparing to explore the northern dungeon"

        context = await memory_service.prepare_memory_context(
            session_id=self.session_id,
            user_prompt=dungeon_prompt,
            correlation_id=self.correlation_id,
        )

        # Should find relevant memories about the dungeon
        relevant_contents = [mem.lower() for mem in context.relevant_memories]
        assert any("dungeon" in content for content in relevant_contents)

        # Should not include irrelevant tavern information
        assert not any("tavern" in content for content in relevant_contents)

    @pytest.mark.asyncio
    async def test_memory_context_token_limit_optimization(self, memory_service):
        """Test memory context optimization when approaching token limits."""
        # Add extensive conversation history
        memory_state = await memory_service._load_memory_state(self.session_id)

        # Add many messages to exceed normal context size
        for i in range(15):
            memory_state.add_message("user", f"User action number {i}")
            memory_state.add_message(
                "assistant", f"DM response to action {i} with detailed description"
            )

        # Prepare context with small token limit
        memory_service.config.max_context_tokens = 500

        context = await memory_service.prepare_memory_context(
            session_id=self.session_id,
            user_prompt="What happens next?",
            correlation_id=self.correlation_id,
        )

        # Verify context was optimized to fit within token limits
        assert context.token_count <= memory_service.config.max_context_tokens

        # Should still have essential information
        assert len(context.recent_events) > 0

    @pytest.mark.asyncio
    async def test_character_knowledge_extraction(self, memory_service):
        """Test extraction of character-specific knowledge from memory."""
        memory_state = await memory_service._load_memory_state(self.session_id)

        # Add conversation with character information
        memory_state.add_message("user", "I am a level 5 fighter with a magic sword")
        memory_state.add_message(
            "assistant", "Noted. You're a skilled fighter with an enchanted blade."
        )
        memory_state.add_message("user", "My sword can cast fireball once per day")
        memory_state.add_message(
            "assistant", "Your magic sword has powerful abilities."
        )
        memory_state.add_message("user", "I need to find the thieves' guild")
        memory_state.add_message(
            "assistant", "You search for information about the guild."
        )

        user_prompt = "I want to use my fireball ability"

        context = await memory_service.prepare_memory_context(
            session_id=self.session_id,
            user_prompt=user_prompt,
            correlation_id=self.correlation_id,
        )

        # Should extract character knowledge about the sword/fireball
        character_knowledge = context.character_knowledge
        assert "general" in character_knowledge
        knowledge_text = " ".join(character_knowledge["general"]).lower()
        assert "sword" in knowledge_text or "fireball" in knowledge_text

    @pytest.mark.asyncio
    async def test_world_state_extraction(self, memory_service):
        """Test extraction of world state information from memory."""
        memory_state = await memory_service._load_memory_state(self.session_id)

        # Add conversation with world-building information
        memory_state.add_message("user", "I look around the village")
        memory_state.add_message(
            "assistant",
            "You are in the village of Oakwood. It's midday and the sun is shining.",
        )
        memory_state.add_message("user", "I check the weather")
        memory_state.add_message(
            "assistant", "It's a beautiful spring day with clear skies."
        )
        memory_state.add_message("user", "Where is the nearest inn?")
        memory_state.add_message(
            "assistant", "The nearest inn is the Oakwood Tavern on the main street."
        )

        user_prompt = "What's the current situation here?"

        context = await memory_service.prepare_memory_context(
            session_id=self.session_id,
            user_prompt=user_prompt,
            correlation_id=self.correlation_id,
        )

        # Should extract world state information
        world_state = context.world_state
        assert "current_location" in world_state or "current_time" in world_state

    @pytest.mark.asyncio
    @patch("packages.backend.agents.dm_graph.ai_client")
    async def test_dm_graph_memory_integration(self, mock_ai_client, dm_graph_service):
        """Test DM graph integration with memory service."""
        # Mock AI client
        mock_ai_client.generate_chat = AsyncMock(
            return_value="The dragon breathes fire! You dodge and counterattack."
        )
        mock_ai_client.is_initialized.return_value = True

        # Initialize DM graph
        initialized = await dm_graph_service.initialize()
        assert initialized

        # Create test memory state
        memory_state = MemoryState(session_id=self.session_id)
        memory_state.add_message("user", "I approach the dragon")
        memory_state.add_message(
            "assistant", "The dragon notices you and spreads its wings."
        )

        user_prompt = "I prepare to attack the dragon"

        # Process interaction
        result = await dm_graph_service.process_interaction(
            user_prompt=user_prompt,
            session_id=self.session_id,
            correlation_id=self.correlation_id,
            campaign_context={"campaign_name": "Dragon's Bane"},
        )

        # Verify interaction completed
        assert result["narrative"] is not None
        assert result["session_id"] == self.session_id
        assert result["correlation_id"] == self.correlation_id

        # Verify no critical errors
        assert "error" not in result or not result.get("error")

    @pytest.mark.asyncio
    async def test_memory_service_health_status(self, memory_service):
        """Test memory service health status reporting."""
        # Add some data to memory
        memory_state = await memory_service._load_memory_state(self.session_id)
        memory_state.add_message("user", "test message")

        # Get health status
        health = memory_service.get_health_status()

        assert isinstance(health, dict)
        assert "status" in health
        assert "active_sessions" in health
        assert "total_operations" in health
        assert "average_operation_time" in health

        # Should report healthy status
        assert health["status"] == "healthy"
        assert health["active_sessions"] >= 1

    @pytest.mark.asyncio
    async def test_memory_session_cleanup(self, memory_service):
        """Test memory cleanup functionality."""
        # Add data to session
        memory_state = await memory_service._load_memory_state(self.session_id)
        memory_state.add_message("user", "test message")

        # Verify session exists
        assert self.session_id in memory_service._session_memory

        # Clear session
        result = memory_service.clear_session_memory(self.session_id)

        assert result is True
        assert self.session_id not in memory_service._session_memory

    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self, memory_service):
        """Test handling of multiple concurrent sessions."""
        session_ids = [f"session_{i}" for i in range(3)]

        # Create multiple sessions
        for session_id in session_ids:
            context = await memory_service.prepare_memory_context(
                session_id=session_id,
                user_prompt="Hello from session",
                correlation_id=f"corr_{session_id}",
            )
            assert context is not None

        # Verify all sessions are isolated
        for session_id in session_ids:
            assert session_id in memory_service._session_memory

        # Verify session data doesn't interfere
        for session_id in session_ids:
            memory_state = await memory_service._load_memory_state(session_id)
            assert memory_state.session_id == session_id


if __name__ == "__main__":
    pytest.main([__file__])
