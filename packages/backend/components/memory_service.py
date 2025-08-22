"""
Memory Service Component for AI Dungeon Master.

This module provides comprehensive memory management functionality including:
- Memory context preparation and injection into AI prompts
- Memory retrieval algorithms with relevance scoring
- Memory summarization for long conversation histories
- Context window optimization for AI token limits
- Integration with DM graph and system prompts
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import MemoryState

logger = get_logger(__name__)


@dataclass
class MemoryContext:
    """Context structure for AI memory integration."""

    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    relevant_memories: List[str] = field(default_factory=list)
    character_knowledge: Dict[str, List[str]] = field(default_factory=dict)
    world_state: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    token_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory context to dictionary."""
        return {
            "recent_events": self.recent_events,
            "relevant_memories": self.relevant_memories,
            "character_knowledge": self.character_knowledge,
            "world_state": self.world_state,
            "summary": self.summary,
            "token_count": self.token_count,
        }


@dataclass
class MemoryConfig:
    """Configuration for memory management."""

    max_context_tokens: int = 2000
    memory_relevance_threshold: float = 0.7
    max_memory_items: int = 50
    cleanup_interval: int = 3600  # 1 hour
    max_recent_events: int = 10
    max_relevant_memories: int = 5
    summarization_threshold: int = 20  # Summarize when conversation exceeds this
    token_estimation_buffer: int = 100  # Buffer for token estimation accuracy


class MemoryService:
    """
    Service for managing AI conversation memory and context.

    Features:
    - Memory context preparation for AI prompts
    - Relevance scoring and filtering
    - Memory summarization for long conversations
    - Context window optimization
    - Performance monitoring
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.logger = get_logger(f"{__name__}.MemoryService")

        # In-memory storage for sessions (in production, this would be a database)
        self._session_memory: Dict[str, MemoryState] = {}
        self._session_contexts: Dict[str, MemoryContext] = {}

        # Performance tracking
        self._operation_times: Dict[str, float] = {}

    async def prepare_memory_context(
        self, session_id: str, user_prompt: str, correlation_id: str
    ) -> MemoryContext:
        """
        Prepare memory context for AI prompt generation.

        Args:
            session_id: Unique session identifier
            user_prompt: Current user prompt
            correlation_id: Correlation ID for tracing

        Returns:
            MemoryContext: Prepared context for AI consumption
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="memory_context_preparation",
                session_id=session_id,
                correlation_id=correlation_id,
            ) as trace_id:
                # Load or create memory state
                memory_state = await self._load_memory_state(session_id)

                # Extract recent events from memory
                recent_events = self._extract_recent_events(memory_state, user_prompt)

                # Find relevant memories
                relevant_memories = await self._find_relevant_memories(
                    memory_state, user_prompt, correlation_id
                )

                # Prepare character knowledge
                character_knowledge = self._extract_character_knowledge(memory_state)

                # Get current world state
                world_state = self._extract_world_state(memory_state)

                # Generate memory summary
                summary = await self._generate_memory_summary(
                    memory_state, recent_events, relevant_memories, correlation_id
                )

                # Optimize for token limits
                context = MemoryContext(
                    recent_events=recent_events,
                    relevant_memories=relevant_memories,
                    character_knowledge=character_knowledge,
                    world_state=world_state,
                    summary=summary,
                )

                # Optimize context size
                context = await self._optimize_context_size(context, correlation_id)

                # Update performance tracking
                execution_time = time.time() - start_time
                self._operation_times[correlation_id] = execution_time

                self.logger.info(
                    "memory_context_prepared",
                    session_id=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                    execution_time=execution_time,
                    token_count=context.token_count,
                    recent_events=len(context.recent_events),
                    relevant_memories=len(context.relevant_memories),
                )

                return context

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                "memory_context_preparation_failed",
                session_id=session_id,
                correlation_id=correlation_id,
                execution_time=execution_time,
                error=str(e),
            )
            # Return minimal context on error
            return MemoryContext(summary="Memory context preparation failed")

    def _extract_recent_events(
        self, memory_state: MemoryState, current_prompt: str
    ) -> List[Dict[str, Any]]:
        """Extract recent events from memory state."""
        recent_messages = memory_state.messages[-self.config.max_recent_events :]

        events = []
        for msg in recent_messages:
            events.append(
                {
                    "type": "message",
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": memory_state.last_activity.isoformat(),
                }
            )

        # Add current prompt as pending event
        events.append(
            {
                "type": "current_prompt",
                "role": "user",
                "content": current_prompt,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return events

    async def _find_relevant_memories(
        self, memory_state: MemoryState, user_prompt: str, correlation_id: str
    ) -> List[str]:
        """Find relevant memories based on user prompt and conversation context."""
        if len(memory_state.messages) <= self.config.summarization_threshold:
            # For shorter conversations, return recent context
            return []

        try:
            # Simple relevance scoring based on keyword matching
            # In a more sophisticated implementation, this could use embeddings
            prompt_keywords = set(user_prompt.lower().split())
            relevant_memories = []

            # Search through message history for relevant content
            for msg in memory_state.messages[-50:]:  # Search last 50 messages
                if msg["role"] == "assistant":  # Only consider AI responses
                    msg_keywords = set(msg["content"].lower().split())
                    relevance_score = len(prompt_keywords.intersection(msg_keywords))

                    if relevance_score > 0:
                        # Calculate normalized relevance score
                        normalized_score = relevance_score / len(prompt_keywords)
                        if normalized_score >= self.config.memory_relevance_threshold:
                            relevant_memories.append(msg["content"])

                            if (
                                len(relevant_memories)
                                >= self.config.max_relevant_memories
                            ):
                                break

            self.logger.debug(
                "relevant_memories_found",
                correlation_id=correlation_id,
                count=len(relevant_memories),
                prompt_keywords=list(prompt_keywords),
            )

            return relevant_memories

        except Exception as e:
            self.logger.warning(
                "memory_relevance_search_failed",
                correlation_id=correlation_id,
                error=str(e),
            )
            return []

    def _extract_character_knowledge(
        self, memory_state: MemoryState
    ) -> Dict[str, List[str]]:
        """Extract character-specific knowledge from memory."""
        character_knowledge = {}

        # Search for character mentions and associated information
        for msg in memory_state.messages:
            content = msg["content"].lower()

            # Look for character names and associated information
            # This is a simplified implementation - could be enhanced with NLP
            if "character" in content or "player" in content:
                # Extract character-related information
                if "character_knowledge" not in character_knowledge:
                    character_knowledge["general"] = []

                if len(character_knowledge["general"]) < 5:  # Limit per category
                    character_knowledge["general"].append(msg["content"])

        return character_knowledge

    def _extract_world_state(self, memory_state: MemoryState) -> Dict[str, Any]:
        """Extract current world state from memory."""
        world_state = {}

        # Look for world-building information
        for msg in memory_state.messages[-20:]:  # Recent messages
            content = msg["content"].lower()

            # Extract location, time, weather, etc.
            if any(
                keyword in content
                for keyword in ["location", "place", "area", "room", "city", "town"]
            ):
                world_state["current_location"] = msg["content"]
            elif any(
                keyword in content
                for keyword in ["time", "hour", "day", "night", "morning", "evening"]
            ):
                world_state["current_time"] = msg["content"]
            elif any(
                keyword in content
                for keyword in ["weather", "storm", "rain", "sun", "cloud"]
            ):
                world_state["current_weather"] = msg["content"]

        return world_state

    async def _generate_memory_summary(
        self,
        memory_state: MemoryState,
        recent_events: List[Dict[str, Any]],
        relevant_memories: List[str],
        correlation_id: str,
    ) -> str:
        """Generate a concise memory summary for AI context."""
        try:
            if len(memory_state.messages) <= self.config.summarization_threshold:
                # For shorter conversations, create simple summary
                user_messages = [
                    msg for msg in memory_state.messages if msg["role"] == "user"
                ]
                if user_messages:
                    last_user_message = user_messages[-1]["content"]
                    return f"Recent context: {last_user_message[:200]}..."
                return "Beginning of conversation."

            # For longer conversations, create structured summary
            summary_parts = []

            # Add conversation overview
            total_messages = len(memory_state.messages)
            user_message_count = len(
                [msg for msg in memory_state.messages if msg["role"] == "user"]
            )
            summary_parts.append(
                f"Conversation with {total_messages} messages ({user_message_count} player actions)."
            )

            # Add recent context
            if recent_events:
                recent_summary = (
                    recent_events[-1]["content"][:100] + "..." if recent_events else ""
                )
                summary_parts.append(f"Most recent: {recent_summary}")

            # Add relevant memories
            if relevant_memories:
                memory_summary = (
                    relevant_memories[0][:100] + "..." if relevant_memories[0] else ""
                )
                summary_parts.append(f"Key context: {memory_summary}")

            return " | ".join(summary_parts)

        except Exception as e:
            self.logger.warning(
                "memory_summary_generation_failed",
                correlation_id=correlation_id,
                error=str(e),
            )
            return "Memory summary unavailable."

    async def _optimize_context_size(
        self, context: MemoryContext, correlation_id: str
    ) -> MemoryContext:
        """Optimize context size to stay within token limits."""
        try:
            # Estimate token count
            context.token_count = self._estimate_token_count(context)

            # If over limit, reduce context
            if context.token_count > self.config.max_context_tokens:
                context = await self._reduce_context_size(context, correlation_id)

                # Re-estimate after reduction
                context.token_count = self._estimate_token_count(context)

            return context

        except Exception as e:
            self.logger.error(
                "context_optimization_failed",
                correlation_id=correlation_id,
                error=str(e),
            )
            return context

    def _estimate_token_count(self, context: MemoryContext) -> int:
        """Estimate token count for the memory context."""
        total_text = ""

        # Add recent events
        for event in context.recent_events:
            total_text += str(event) + " "

        # Add relevant memories
        total_text += " ".join(context.relevant_memories) + " "

        # Add character knowledge
        for knowledge_list in context.character_knowledge.values():
            total_text += " ".join(knowledge_list) + " "

        # Add world state
        total_text += str(context.world_state) + " "

        # Add summary
        total_text += context.summary + " "

        # Rough estimation: 1 token ≈ 4 characters
        estimated_tokens = len(total_text) // 4
        return estimated_tokens + self.config.token_estimation_buffer

    async def _reduce_context_size(
        self, context: MemoryContext, correlation_id: str
    ) -> MemoryContext:
        """Reduce context size to fit within token limits."""
        # Remove least important information first
        reductions = []

        # Reduce relevant memories if too many
        if len(context.relevant_memories) > 3:
            context.relevant_memories = context.relevant_memories[:3]
            reductions.append("reduced_relevant_memories")

        # Reduce recent events if too many
        if len(context.recent_events) > 5:
            context.recent_events = context.recent_events[-5:]  # Keep most recent
            reductions.append("reduced_recent_events")

        # Truncate character knowledge
        for char_name, knowledge_list in context.character_knowledge.items():
            if len(knowledge_list) > 3:
                context.character_knowledge[char_name] = knowledge_list[:3]
                reductions.append(f"reduced_character_knowledge_{char_name}")

        # Shorten summary if needed
        if len(context.summary) > 500:
            context.summary = context.summary[:500] + "..."
            reductions.append("truncated_summary")

        if reductions:
            self.logger.info(
                "context_size_reduced",
                correlation_id=correlation_id,
                reductions=reductions,
            )

        return context

    async def update_memory_after_interaction(
        self, session_id: str, user_prompt: str, ai_response: str, correlation_id: str
    ) -> None:
        """Update memory state after a conversation interaction."""
        try:
            # Load current memory state
            memory_state = await self._load_memory_state(session_id)

            # Add user message
            memory_state.add_message("user", user_prompt)

            # Add AI response
            memory_state.add_message("assistant", ai_response)

            # Clean up old memories if needed
            await self._cleanup_old_memories(memory_state, correlation_id)

            # Persist updated memory
            await self._persist_memory_state(memory_state)

            self.logger.debug(
                "memory_updated_after_interaction",
                session_id=session_id,
                correlation_id=correlation_id,
                total_messages=len(memory_state.messages),
            )

        except Exception as e:
            self.logger.error(
                "memory_update_failed",
                session_id=session_id,
                correlation_id=correlation_id,
                error=str(e),
            )

    async def _load_memory_state(self, session_id: str) -> MemoryState:
        """Load memory state for a session."""
        # In a real implementation, this would load from database
        if session_id not in self._session_memory:
            self._session_memory[session_id] = MemoryState(session_id=session_id)

        return self._session_memory[session_id]

    async def _persist_memory_state(self, memory_state: MemoryState) -> None:
        """Persist memory state."""
        # In a real implementation, this would save to database
        self._session_memory[memory_state.session_id] = memory_state

    async def _cleanup_old_memories(
        self, memory_state: MemoryState, correlation_id: str
    ) -> None:
        """Clean up old memories to prevent unlimited growth."""
        try:
            # Remove very old messages if exceeding limit
            if len(memory_state.messages) > self.config.max_memory_items * 2:
                # Keep only the most recent messages
                keep_count = self.config.max_memory_items
                memory_state.messages = memory_state.messages[-keep_count:]

                self.logger.info(
                    "old_memories_cleaned",
                    session_id=memory_state.session_id,
                    correlation_id=correlation_id,
                    messages_removed=len(memory_state.messages) - keep_count,
                )

        except Exception as e:
            self.logger.warning(
                "memory_cleanup_failed",
                session_id=memory_state.session_id,
                correlation_id=correlation_id,
                error=str(e),
            )

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the memory service."""
        return {
            "status": "healthy",
            "active_sessions": len(self._session_memory),
            "total_operations": len(self._operation_times),
            "average_operation_time": sum(self._operation_times.values())
            / max(len(self._operation_times), 1),
            "config": {
                "max_context_tokens": self.config.max_context_tokens,
                "max_memory_items": self.config.max_memory_items,
                "memory_relevance_threshold": self.config.memory_relevance_threshold,
            },
        }

    def clear_session_memory(self, session_id: str) -> bool:
        """Clear memory for a specific session."""
        if session_id in self._session_memory:
            del self._session_memory[session_id]
            if session_id in self._session_contexts:
                del self._session_contexts[session_id]
            return True
        return False


# Global memory service instance
memory_service = MemoryService()
