"""
Unit tests for the DM Graph component.

Tests cover:
- Graph initialization and compilation
- Memory state management and transitions
- AI interaction node with mocked AI client
- Error handling and recovery mechanisms
- Tracing integration and performance monitoring
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from packages.backend.agents.dm_graph import DMGraphConfig, DMGraphService, DMGraphState
from packages.shared.models import MemoryState


class TestDMGraphConfig:
    """Test the DMGraphConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DMGraphConfig()

        assert config.max_memory_messages == 50
        assert config.max_scratchpad_items == 20
        assert config.enable_tracing is True
        assert config.enable_performance_monitoring is True
        assert isinstance(config.fallback_responses, dict)
        assert "ai_unavailable" in config.fallback_responses
        assert "processing_error" in config.fallback_responses


class TestDMGraphService:
    """Test the DMGraphService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = DMGraphConfig()
        self.service = DMGraphService(self.config)

    def test_initialization_without_langgraph(self):
        """Test initialization when LangGraph is not available."""
        with patch("packages.backend.agents.dm_graph.LANGGRAPH_AVAILABLE", False):
            service = DMGraphService()
            result = asyncio.run(service.initialize())
            assert result is False
            assert not service.is_initialized()

    @patch("packages.backend.agents.dm_graph.ai_client")
    def test_initialization_success(self, mock_ai_client):
        """Test successful service initialization."""
        mock_ai_client.is_initialized.return_value = True

        with patch.object(
            self.service, "_build_graph", new_callable=AsyncMock
        ) as mock_build:
            mock_build.return_value = Mock()

            result = asyncio.run(self.service.initialize())

            assert result is True
            assert self.service.is_initialized()
            assert self.service._graph is not None

            mock_build.assert_called_once()

    def test_get_health_status_not_initialized(self):
        """Test health status when service is not initialized."""
        status = self.service.get_health_status()

        assert status["status"] == "unhealthy"
        assert status["langgraph_available"] is not None
        assert status["ai_client_initialized"] is False

    def test_extract_narrative_basic(self):
        """Test basic narrative extraction from AI response."""
        ai_response = (
            "As the DM, you carefully examine the room and find a hidden door."
        )
        narrative = self.service._extract_narrative(ai_response)

        assert "you carefully examine" in narrative.lower()

    def test_extract_narrative_with_prefix_removal(self):
        """Test narrative extraction with prefix removal."""
        ai_response = "DM: You discover a treasure chest in the corner."
        narrative = self.service._extract_narrative(ai_response)

        assert not narrative.startswith("DM:")
        assert "treasure chest" in narrative

    def test_fallback_system_prompt(self):
        """Test fallback system prompt generation."""
        prompt = self.service._get_fallback_system_prompt()

        assert "AI Dungeon Master" in prompt
        assert "Dungeons & Dragons" in prompt
        assert len(prompt) > 100


class TestMemoryStateIntegration:
    """Test MemoryState integration with DM graph."""

    def test_memory_state_creation(self):
        """Test creating memory state for DM interactions."""
        session_id = "dm_session_123"
        memory_state = MemoryState(session_id=session_id)

        assert memory_state.session_id == session_id
        assert memory_state.messages == []
        assert memory_state.context == {}
        assert memory_state.scratchpad == []
        assert memory_state.turn_count == 0

    def test_memory_state_message_management(self):
        """Test adding messages to memory state."""
        memory_state = MemoryState(session_id="test_session")

        memory_state.add_message("user", "I want to investigate the room")
        assert memory_state.turn_count == 1
        assert len(memory_state.messages) == 1
        assert memory_state.messages[0]["role"] == "user"

        memory_state.add_message("assistant", "You examine the room carefully.")
        assert (
            memory_state.turn_count == 1
        )  # Should not increment for assistant messages
        assert len(memory_state.messages) == 2

    def test_memory_state_scratchpad(self):
        """Test scratchpad functionality."""
        memory_state = MemoryState(session_id="test_session")

        memory_state.add_to_scratchpad("Player is investigating a statue")
        memory_state.add_to_scratchpad("Player has detect magic ability")

        assert len(memory_state.scratchpad) == 2
        assert "statue" in memory_state.scratchpad[0]

        memory_state.clear_scratchpad()
        assert len(memory_state.scratchpad) == 0

    def test_memory_state_serialization(self):
        """Test memory state serialization."""
        memory_state = MemoryState(
            session_id="test_session", context={"campaign": "Lost Mines"}, turn_count=5
        )
        memory_state.add_message("user", "test message")

        # Test serialization
        data = memory_state.to_dict()
        assert isinstance(data, dict)
        assert data["session_id"] == "test_session"
        assert data["context"]["campaign"] == "Lost Mines"
        assert data["turn_count"] == 5
        assert len(data["messages"]) == 1

        # Test deserialization
        restored = MemoryState.from_dict(data)
        assert restored.session_id == memory_state.session_id
        assert restored.context == memory_state.context
        assert restored.turn_count == memory_state.turn_count
        assert len(restored.messages) == 1


class TestDMGraphErrorHandling:
    """Test error handling in DM graph operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = DMGraphService()
        self.correlation_id = "test-correlation-123"

    def test_process_prompt_node_error_handling(self):
        """Test error handling in prompt processing node."""
        state = DMGraphState(
            user_prompt="",  # Empty prompt should cause error
            memory_state=MemoryState(session_id="test_session"),
            system_prompt="",
            ai_response=None,
            narrative_response=None,
            error=None,
            correlation_id=self.correlation_id,
        )

        result = asyncio.run(self.service._process_prompt_node(state))

        assert "error" in result
        assert result["error"] is not None

    def test_compile_context_node_error_handling(self):
        """Test error handling in context compilation node."""
        state = DMGraphState(
            user_prompt="test prompt",
            memory_state=MemoryState(session_id="test_session"),
            system_prompt="",
            ai_response=None,
            narrative_response=None,
            error=None,
            correlation_id=self.correlation_id,
        )

        # Mock both prompt manager and memory service to raise errors
        with patch(
            "packages.backend.agents.dm_graph.prompt_manager"
        ) as mock_prompt_manager, patch(
            "packages.backend.agents.dm_graph.memory_service"
        ) as mock_memory_service:
            mock_prompt_manager.create_core_dm_prompt.side_effect = Exception(
                "Prompt creation failed"
            )
            mock_memory_service.prepare_memory_context.side_effect = Exception(
                "Memory context preparation failed"
            )

            result = asyncio.run(self.service._compile_context_node(state))

            assert "error" in result
            assert result["error"] is not None
            assert "Context compilation failed" in result["error"]

    def test_should_handle_error_logic(self):
        """Test error handling decision logic."""
        # Test with error present
        state_with_error = DMGraphState(
            user_prompt="test",
            memory_state=MemoryState(session_id="test"),
            system_prompt="",
            ai_response=None,
            narrative_response=None,
            error="Some error occurred",
            correlation_id=self.correlation_id,
        )

        result = self.service._should_handle_error(state_with_error)
        assert result == "error"

        # Test without error
        state_without_error = DMGraphState(
            user_prompt="test",
            memory_state=MemoryState(session_id="test"),
            system_prompt="",
            ai_response=None,
            narrative_response=None,
            error=None,
            correlation_id=self.correlation_id,
        )

        result = self.service._should_handle_error(state_without_error)
        assert result == "continue"
