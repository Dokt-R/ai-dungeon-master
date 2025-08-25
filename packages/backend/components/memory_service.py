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
from packages.shared.db import get_async_session
from packages.shared.logging_config import get_logger
from packages.shared.models import MemoryState, MemoryStateModel
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError
import json

# Try to import tiktoken for accurate token counting
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

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

        # Token counting setup
        self._tokenizer = None
        self._encoding_name = "cl100k_base"  # GPT-3.5/4 tokenizer
        self._initialize_tokenizer()

        # Performance tracking
        self._operation_times: Dict[str, float] = {}

        # Cache for recently accessed memory states (performance optimization)
        self._memory_cache: Dict[str, MemoryState] = {}
        self._context_cache: Dict[str, MemoryContext] = {}
        self._cache_max_age = 300  # 5 minutes cache

    def _initialize_tokenizer(self) -> None:
        """Initialize tokenizer for accurate token counting."""
        if TIKTOKEN_AVAILABLE:
            try:
                self._tokenizer = tiktoken.get_encoding(self._encoding_name)
                self.logger.debug("tiktoken_initialized", encoding=self._encoding_name)
            except Exception as e:
                self.logger.warning(
                    "tiktoken_initialization_failed",
                    error=str(e),
                    encoding=self._encoding_name,
                )
                self._tokenizer = None
        else:
            self.logger.info("tiktoken_not_available_using_fallback")
            self._tokenizer = None

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken if available, otherwise use improved approximation.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Use tiktoken if available (most accurate)
        if self._tokenizer:
            try:
                return len(self._tokenizer.encode(text))
            except Exception as e:
                self.logger.warning("tiktoken_counting_failed", error=str(e))

        # Improved approximation based on character and word analysis
        # This is more accurate than the simple 1:4 ratio
        char_count = len(text)
        word_count = len(text.split())

        # Base approximation: 1 token ≈ 4 characters
        base_tokens = char_count // 4

        # Adjustments for different text characteristics
        adjustments = 0

        # Add tokens for words (each word typically needs extra tokens for word boundaries)
        adjustments += word_count // 3

        # Add tokens for punctuation and special characters
        punctuation_count = sum(
            1 for char in text if char in "!@#$%^&*()_+-=[]{}|;:,.<>?"
        )
        adjustments += punctuation_count // 2

        # Add tokens for numbers (numbers often take more tokens)
        number_count = sum(1 for char in text if char.isdigit())
        adjustments += number_count // 2

        # Add tokens for uppercase words (proper nouns, etc.)
        uppercase_word_count = sum(
            1 for word in text.split() if word and word[0].isupper()
        )
        adjustments += uppercase_word_count // 4

        # Add tokens for whitespace (each whitespace sequence takes tokens)
        whitespace_sequences = len(text.split()) - 1 if text.split() else 0
        adjustments += whitespace_sequences // 4

        total_tokens = base_tokens + adjustments

        # Ensure minimum token count and add buffer for safety
        return max(1, total_tokens) + self.config.token_estimation_buffer

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
        # Process conversations with any messages, not just long ones
        if len(memory_state.messages) == 0:
            return []

        try:
            # Simple relevance scoring based on keyword matching
            # In a more sophisticated implementation, this could use embeddings

            # Filter out common stop words to improve relevance matching
            stop_words = {"i", "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "this", "that", "these", "those", "i'm", "i've", "i'll", "you", "me", "my", "your", "it", "its", "they", "them", "their"}

            prompt_words = [word.strip('.,!?;:"\'') for word in user_prompt.lower().split()]
            prompt_keywords = set(word for word in prompt_words if word not in stop_words and len(word) > 2)

            relevant_memories = []

            # Search through message history for relevant content
            for msg in memory_state.messages[-50:]:  # Search last 50 messages
                if msg["role"] == "assistant":  # Only consider AI responses
                    msg_words = [word.strip('.,!?;:"\'') for word in msg["content"].lower().split()]
                    msg_keywords = set(word for word in msg_words if word not in stop_words and len(word) > 2)
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
                total_messages=len(memory_state.messages),
                assistant_messages=len([msg for msg in memory_state.messages if msg["role"] == "assistant"]),
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
                if "general" not in character_knowledge:
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
        """Estimate token count for the memory context using improved counting."""
        total_tokens = 0
        text_parts = []

        # Add recent events
        for event in context.recent_events:
            event_text = f"{event.get('role', 'unknown')}: {event.get('content', '')}"
            text_parts.append(event_text)

        # Add relevant memories
        if context.relevant_memories:
            memories_text = " ".join(context.relevant_memories)
            text_parts.append(f"Relevant memories: {memories_text}")

        # Add character knowledge
        for char_name, knowledge_list in context.character_knowledge.items():
            if knowledge_list:
                char_text = f"Knowledge about {char_name}: " + " ".join(knowledge_list)
                text_parts.append(char_text)

        # Add world state
        if context.world_state:
            world_parts = []
            for key, value in context.world_state.items():
                if value:
                    world_parts.append(f"{key}: {value}")
            if world_parts:
                world_text = "World state: " + "; ".join(world_parts)
                text_parts.append(world_text)

        # Add summary
        if context.summary:
            text_parts.append(f"Summary: {context.summary}")

        # Count tokens for each part and sum them up
        for text_part in text_parts:
            total_tokens += self._count_tokens(text_part)

        # Add buffer for safety and separators
        separator_tokens = len(text_parts) * 2  # Rough estimate for separators
        return total_tokens + separator_tokens + self.config.token_estimation_buffer

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
        """Load memory state for a session from database with caching."""
        try:
            # Check cache first
            if session_id in self._memory_cache:
                cached_memory = self._memory_cache[session_id]
                # Check if cache is still valid (within max age)
                if (
                    datetime.utcnow() - cached_memory.last_activity
                ).total_seconds() < self._cache_max_age:
                    return cached_memory

            # Load from database
            async with get_async_session() as session:
                result = await session.execute(
                    select(MemoryStateModel).where(
                        MemoryStateModel.session_id == session_id
                    )
                )
                memory_record = result.scalar_one_or_none()

                if memory_record:
                    # Deserialize from database record
                    memory_state = MemoryState(
                        session_id=memory_record.session_id,
                        messages=json.loads(memory_record.messages),
                        context=json.loads(memory_record.context),
                        turn_count=memory_record.turn_count,
                        scratchpad=json.loads(memory_record.scratchpad),
                        last_activity=memory_record.last_activity,
                    )
                else:
                    # Create new memory state
                    memory_state = MemoryState(session_id=session_id)

                # Update cache
                self._memory_cache[session_id] = memory_state
                return memory_state

        except SQLAlchemyError as e:
            self.logger.error(
                "database_error_loading_memory", session_id=session_id, error=str(e)
            )
            # Fallback to new memory state on database error
            return MemoryState(session_id=session_id)
        except Exception as e:
            self.logger.error(
                "error_loading_memory", session_id=session_id, error=str(e)
            )
            # Fallback to new memory state
            return MemoryState(session_id=session_id)

    async def _persist_memory_state(self, memory_state: MemoryState) -> None:
        """Persist memory state to database."""
        try:
            async with get_async_session() as session:
                # Check if record exists
                result = await session.execute(
                    select(MemoryStateModel).where(
                        MemoryStateModel.session_id == memory_state.session_id
                    )
                )
                existing_record = result.scalar_one_or_none()

                # Serialize memory state for database storage
                serialized_data = {
                    "messages": json.dumps(memory_state.messages),
                    "context": json.dumps(memory_state.context),
                    "scratchpad": json.dumps(memory_state.scratchpad),
                    "turn_count": memory_state.turn_count,
                    "total_messages": len(memory_state.messages),
                    "last_activity": memory_state.last_activity.isoformat(),
                    "last_save": datetime.utcnow().isoformat(),
                }

                if existing_record:
                    # Update existing record
                    await session.execute(
                        update(MemoryStateModel)
                        .where(MemoryStateModel.session_id == memory_state.session_id)
                        .values(**serialized_data)
                    )
                else:
                    # Create new record
                    new_record = MemoryStateModel(
                        session_id=memory_state.session_id, **serialized_data
                    )
                    session.add(new_record)

                await session.commit()

                # Update cache
                self._memory_cache[memory_state.session_id] = memory_state

                self.logger.debug(
                    "memory_state_persisted",
                    session_id=memory_state.session_id,
                    total_messages=len(memory_state.messages),
                )

        except SQLAlchemyError as e:
            self.logger.error(
                "database_error_persisting_memory",
                session_id=memory_state.session_id,
                error=str(e),
            )
            # Continue without failing - memory will be lost on restart but service continues
        except Exception as e:
            self.logger.error(
                "error_persisting_memory",
                session_id=memory_state.session_id,
                error=str(e),
            )

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
        cache_sessions = len(self._memory_cache)

        return {
            "status": "healthy",
            "active_sessions": cache_sessions,
            "cached_sessions": cache_sessions,
            "cached_contexts": len(self._context_cache),
            "total_operations": len(self._operation_times),
            "average_operation_time": sum(self._operation_times.values())
            / max(len(self._operation_times), 1),
            "database_enabled": True,
            "tokenizer_available": self._tokenizer is not None,
            "cache_max_age": self._cache_max_age,
            "config": {
                "max_context_tokens": self.config.max_context_tokens,
                "max_memory_items": self.config.max_memory_items,
                "memory_relevance_threshold": self.config.memory_relevance_threshold,
                "token_estimation_buffer": self.config.token_estimation_buffer,
            },
        }

    def clear_session_memory(self, session_id: str) -> bool:
        """Clear memory for a specific session from both cache and database."""
        try:
            # Clear from cache
            cleared_cache = False
            if session_id in self._memory_cache:
                del self._memory_cache[session_id]
                cleared_cache = True

            if session_id in self._context_cache:
                del self._context_cache[session_id]
                cleared_cache = True

            # Clear from database
            cleared_db = False
            try:
                import asyncio

                # Run database operation in background to avoid blocking
                asyncio.create_task(self._delete_memory_from_db(session_id))
                cleared_db = True
            except Exception as e:
                self.logger.warning(
                    "failed_to_queue_db_cleanup", session_id=session_id, error=str(e)
                )

            return cleared_cache or cleared_db

        except Exception as e:
            self.logger.error(
                "error_clearing_session_memory", session_id=session_id, error=str(e)
            )
            return False

    async def _delete_memory_from_db(self, session_id: str) -> None:
        """Delete memory state from database."""
        try:
            async with get_async_session() as session:
                await session.execute(
                    delete(MemoryStateModel).where(
                        MemoryStateModel.session_id == session_id
                    )
                )
                await session.commit()

                self.logger.debug("memory_deleted_from_db", session_id=session_id)

        except SQLAlchemyError as e:
            self.logger.error(
                "database_error_deleting_memory", session_id=session_id, error=str(e)
            )
        except Exception as e:
            self.logger.error(
                "error_deleting_memory_from_db", session_id=session_id, error=str(e)
            )


# Global memory service instance
memory_service = MemoryService()
