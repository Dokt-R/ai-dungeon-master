"""
Unit tests for the Memory Service component.

Tests cover:
- Memory context preparation and injection
- Memory retrieval algorithms and relevance scoring
- Memory summarization for long conversations
- Context window optimization and token limits
- Memory state management and persistence
- Performance monitoring and error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from packages.backend.components.memory_service import (
    MemoryService,
    MemoryContext,
    MemoryConfig,
    memory_service
)
from packages.shared.models import MemoryState
from packages.backend.components.observability_service import observability_service


class TestMemoryConfig:
    """Test the MemoryConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MemoryConfig()

        assert config.max_context_tokens == 2000
        assert config.memory_relevance_threshold == 0.7
        assert config.max_memory_items == 50
        assert config.cleanup_interval == 3600
        assert config.max_recent_events == 10
        assert config.max_relevant_memories == 5
        assert config.summarization_threshold == 20
        assert config.token_estimation_buffer == 100

    def test_custom_config(self):
        """Test custom configuration values."""
        config = MemoryConfig(
            max_context_tokens=1500,
            memory_relevance_threshold=0.8,
            max_memory_items=100,
            max_recent_events=15
        )

        assert config.max_context_tokens == 1500
        assert config.memory_relevance_threshold == 0.8
        assert config.max_memory_items == 100
        assert config.max_recent_events == 15


class TestMemoryContext:
    """Test the MemoryContext class."""

    def test_memory_context_creation(self):
        """Test creating a memory context."""
        context = MemoryContext(
            recent_events=[{"type": "message", "content": "test"}],
            relevant_memories=["memory1", "memory2"],
            character_knowledge={"alice": ["fighter", "level 3"]},
            world_state={"location": "dungeon"},
            summary="Test summary",
            token_count=150
        )

        assert len(context.recent_events) == 1
        assert len(context.relevant_memories) == 2
        assert context.character_knowledge["alice"] == ["fighter", "level 3"]
        assert context.world_state["location"] == "dungeon"
        assert context.summary == "Test summary"
        assert context.token_count == 150

    def test_memory_context_to_dict(self):
        """Test converting memory context to dictionary."""
        context = MemoryContext(
            recent_events=[{"type": "message", "content": "test"}],
            summary="Test summary"
        )

        data = context.to_dict()

        assert isinstance(data, dict)
        assert data["recent_events"] == [{"type": "message", "content": "test"}]
        assert data["summary"] == "Test summary"
        assert data["token_count"] == 0


class TestMemoryService:
    """Test the MemoryService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = MemoryConfig()
        self.service = MemoryService(self.config)

    def test_initialization(self):
        """Test service initialization."""
        assert self.service.config is self.config
        assert self.service._session_memory == {}
        assert self.service._session_contexts == {}
        assert self.service._operation_times == {}

    @patch('packages.backend.components.memory_service.observability_service')
    def test_prepare_memory_context_short_conversation(self, mock_obs):
        """Test memory context preparation for short conversation."""
        mock_obs.trace_operation.return_value.__enter__ = Mock(return_value="test-trace")
        mock_obs.trace_operation.return_value.__exit__ = Mock(return_value=None)

        # Create memory state with short conversation
        memory_state = MemoryState(session_id="test_session")
        memory_state.add_message("user", "I want to investigate the room")

        # Mock the _load_memory_state method
        with patch.object(self.service, '_load_memory_state', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = memory_state

            result = asyncio.run(self.service.prepare_memory_context(
                session_id="test_session",
                user_prompt="I look around",
                correlation_id="test-correlation"
            ))

            assert isinstance(result, MemoryContext)
            assert len(result.recent_events) >= 1
            assert "I look around" in str(result.recent_events)

    @patch('packages.backend.components.memory_service.observability_service')
    def test_prepare_memory_context_long_conversation(self, mock_obs):
        """Test memory context preparation for long conversation."""
        mock_obs.trace_operation.return_value.__enter__ = Mock(return_value="test-trace")
        mock_obs.trace_operation.return_value.__exit__ = Mock(return_value=None)

        # Create memory state with long conversation
        memory_state = MemoryState(session_id="test_session")

        # Add many messages to exceed summarization threshold
        for i in range(25):
            memory_state.add_message("user", f"Action {i}")
            memory_state.add_message("assistant", f"Response {i}")

        with patch.object(self.service, '_load_memory_state', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = memory_state

            result = asyncio.run(self.service.prepare_memory_context(
                session_id="test_session",
                user_prompt="What's the current situation?",
                correlation_id="test-correlation"
            ))

            assert isinstance(result, MemoryContext)
            assert result.summary != ""
            assert "Conversation with" in result.summary

    def test_extract_recent_events(self):
        """Test extraction of recent events from memory."""
        memory_state = MemoryState(session_id="test_session")
        memory_state.add_message("user", "I open the door")
        memory_state.add_message("assistant", "You open the creaky door")

        events = self.service._extract_recent_events(memory_state, "I look inside")

        assert len(events) == 3  # 2 previous + 1 current
        assert events[0]["role"] == "user"
        assert events[0]["content"] == "I open the door"
        assert events[-1]["role"] == "user"
        assert events[-1]["content"] == "I look inside"

    def test_extract_recent_events_limit(self):
        """Test recent events extraction with limit."""
        memory_state = MemoryState(session_id="test_session")

        # Add more events than the limit
        for i in range(15):
            memory_state.add_message("user", f"Action {i}")

        # Temporarily reduce the limit
        self.service.config.max_recent_events = 5
        events = self.service._extract_recent_events(memory_state, "Final action")

        assert len(events) == 6  # 5 previous + 1 current

    def test_find_relevant_memories_keyword_match(self):
        """Test finding relevant memories based on keyword matching."""
        memory_state = MemoryState(session_id="test_session")

        # Add messages with relevant keywords
        memory_state.add_message("assistant", "You find a treasure chest in the corner of the room.")
        memory_state.add_message("assistant", "The goblin guard is blocking the exit.")
        memory_state.add_message("assistant", "You discover an ancient sword on the pedestal.")

        relevant = asyncio.run(self.service._find_relevant_memories(
            memory_state,
            "I want to get the treasure",
            "test-correlation"
        ))

        assert len(relevant) > 0
        assert any("treasure chest" in memory.lower() for memory in relevant)

    def test_find_relevant_memories_no_match(self):
        """Test finding relevant memories when no matches exist."""
        memory_state = MemoryState(session_id="test_session")
        memory_state.add_message("assistant", "The weather is nice today.")

        relevant = asyncio.run(self.service._find_relevant_memories(
            memory_state,
            "I want to fight the dragon",
            "test-correlation"
        ))

        assert len(relevant) == 0

    def test_extract_character_knowledge(self):
        """Test extraction of character knowledge."""
        memory_state = MemoryState(session_id="test_session")
        memory_state.add_message("assistant", "Eldrin the fighter has a magical sword.")
        memory_state.add_message("assistant", "Thalor the wizard knows fire magic.")

        knowledge = self.service._extract_character_knowledge(memory_state)

        assert "general" in knowledge
        assert len(knowledge["general"]) > 0

    def test_extract_world_state(self):
        """Test extraction of world state."""
        memory_state = MemoryState(session_id="test_session")
        memory_state.add_message("assistant", "You are in the dark dungeon.")
        memory_state.add_message("assistant", "It's nighttime in the forest.")

        world_state = self.service._extract_world_state(memory_state)

        assert "current_location" in world_state or "current_time" in world_state

    def test_generate_memory_summary_short(self):
        """Test memory summary generation for short conversation."""
        memory_state = MemoryState(session_id="test_session")
        memory_state.add_message("user", "I look around")

        summary = asyncio.run(self.service._generate_memory_summary(
            memory_state,
            [{"type": "message", "content": "I look around"}],
            [],
            "test-correlation"
        ))

        assert "Beginning of conversation" in summary

    def test_generate_memory_summary_long(self):
        """Test memory summary generation for long conversation."""
        memory_state = MemoryState(session_id="test_session")

        for i in range(25):
            memory_state.add_message("user", f"Action {i}")
            memory_state.add_message("assistant", f"Response {i}")

        summary = asyncio.run(self.service._generate_memory_summary(
            memory_state,
            [{"type": "message", "content": "Most recent action"}],
            ["Important memory"],
            "test-correlation"
        ))

        assert "Conversation with" in summary
        assert "50 messages" in summary

    def test_estimate_token_count(self):
        """Test token count estimation."""
        context = MemoryContext(
            recent_events=[{"content": "test event"}],
            relevant_memories=["memory 1", "memory 2"],
            summary="Test summary"
        )

        token_count = self.service._estimate_token_count(context)

        assert token_count > 0
        assert token_count == len(str(context.to_dict())) // 4 + self.config.token_estimation_buffer

    def test_optimize_context_size_under_limit(self):
        """Test context optimization when under token limit."""
        context = MemoryContext(
            summary="Short summary",
            token_count=500
        )

        optimized = asyncio.run(self.service._optimize_context_size(context, "test-correlation"))

        assert optimized.token_count == 500
        assert optimized.summary == "Short summary"

    def test_optimize_context_size_over_limit(self):
        """Test context optimization when over token limit."""
        # Create context that will exceed limit
        context = MemoryContext(
            relevant_memories=[f"Memory {i}" for i in range(10)],
            summary="x" * 1000,  # Very long summary
            token_count=2500
        )

        optimized = asyncio.run(self.service._optimize_context_size(context, "test-correlation"))

        assert optimized.token_count < 2500  # Should be reduced
        assert len(optimized.relevant_memories) <= 3  # Should be reduced
        assert len(optimized.summary) <= 500  # Should be truncated

    @patch('packages.backend.components.memory_service.observability_service')
    def test_update_memory_after_interaction(self, mock_obs):
        """Test memory update after interaction."""
        mock_obs.trace_operation.return_value.__enter__ = Mock(return_value="test-trace")
        mock_obs.trace_operation.return_value.__exit__ = Mock(return_value=None)

        asyncio.run(self.service.update_memory_after_interaction(
            session_id="test_session",
            user_prompt="I attack the goblin",
            ai_response="You strike the goblin with your sword!",
            correlation_id="test-correlation"
        ))

        # Check that memory was stored
        assert "test_session" in self.service._session_memory
        memory_state = self.service._session_memory["test_session"]

        assert len(memory_state.messages) == 2
        assert memory_state.messages[0]["role"] == "user"
        assert memory_state.messages[1]["role"] == "assistant"
        assert memory_state.turn_count == 1

    def test_get_health_status(self):
        """Test health status reporting."""
        status = self.service.get_health_status()

        assert status["status"] == "healthy"
        assert "active_sessions" in status
        assert "total_operations" in status
        assert "average_operation_time" in status
        assert "config" in status

    def test_clear_session_memory(self):
        """Test clearing session memory."""
        # Add some memory
        self.service._session_memory["test_session"] = MemoryState(session_id="test_session")
        self.service._session_contexts["test_session"] = MemoryContext()

        # Clear it
        result = self.service.clear_session_memory("test_session")

        assert result is True
        assert "test_session" not in self.service._session_memory
        assert "test_session" not in self.service._session_contexts

    def test_clear_session_memory_not_found(self):
        """Test clearing memory for non-existent session."""
        result = self.service.clear_session_memory("non_existent")

        assert result is False


class TestGlobalMemoryServiceInstance:
    """Test the global memory service instance."""

    def test_global_instance_exists(self):
        """Test that the global instance exists."""
        assert memory_service is not None
        assert isinstance(memory_service, MemoryService)

    def test_global_instance_health(self):
        """Test global instance health status."""
        status = memory_service.get_health_status()

        assert isinstance(status, dict)
        assert "status" in status
        assert "config" in status


class TestMemoryServiceErrorHandling:
    """Test error handling in memory service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MemoryService()

    @patch('packages.backend.components.memory_service.observability_service')
    def test_prepare_context_error_handling(self, mock_obs):
        """Test error handling in context preparation."""
        mock_obs.trace_operation.side_effect = Exception("Tracing failed")

        result = asyncio.run(self.service.prepare_memory_context(
            session_id="test_session",
            user_prompt="test prompt",
            correlation_id="test-correlation"
        ))

        # Should return minimal context on error
        assert isinstance(result, MemoryContext)
        assert "failed" in result.summary.lower()

    def test_memory_update_error_handling(self):
        """Test error handling in memory updates."""
        # This should not raise an exception even if there are issues
        asyncio.run(self.service.update_memory_after_interaction(
            session_id="test_session",
            user_prompt="test prompt",
            ai_response="test response",
            correlation_id="test-correlation"
        ))

        # Memory should still be created
        assert "test_session" in self.service._session_memory