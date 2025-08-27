"""
DM Graph Implementation using LangGraph framework.

This module implements the core AI Dungeon Master graph using LangGraph,
integrating conversational memory, AI client interactions, system prompts,
and comprehensive error handling with observability.

Key Features:
- LangGraph state machine for DM interactions
- Conversational memory with scratchpad functionality
- AI client integration with retry and circuit breaker patterns
- System prompt integration with template-based generation
- Comprehensive error handling and recovery
- LangSmith tracing integration
- Performance monitoring and logging
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph
    from langgraph.prebuilt import ToolNode
    from typing_extensions import Annotated
    from operator import add

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    ToolNode = None
    MemorySaver = None
    Annotated = None
    add = None

from packages.backend.agents.prompts import prompt_manager
from packages.backend.components.ai_client import ai_client
from packages.backend.components.memory_service import memory_service
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import MemoryState

logger = get_logger(__name__)


# LangGraph State Definition
class DMGraphState(TypedDict):
    """LangGraph state for DM interactions."""

    user_prompt: str
    memory_state: MemoryState
    system_prompt: str
    ai_response: Optional[str]
    narrative_response: Optional[str]
    error: Optional[str]  # Keep single error to avoid concurrent updates
    correlation_id: str
    context_messages: Optional[List[Dict[str, str]]]
    memory_context: Optional[Any]
    processing_stage: str  # Track which stage we're in


@dataclass
class DMGraphConfig:
    """Configuration for DM graph execution."""

    max_memory_messages: int = 50
    max_scratchpad_items: int = 20
    enable_tracing: bool = True
    enable_performance_monitoring: bool = True
    fallback_responses: Dict[str, str] = field(
        default_factory=lambda: {
            "ai_unavailable": "The DM seems to be having trouble responding right now. Please try again.",
            "processing_error": "Something went wrong processing your request. The DM will respond shortly.",
        }
    )


class DMGraphError(Exception):
    """Base exception for DM graph errors."""

    pass


class MemoryError(DMGraphError):
    """Raised when memory operations fail."""

    pass


class AIError(DMGraphError):
    """Raised when AI service operations fail."""

    pass


class PromptError(DMGraphError):
    """Raised when prompt processing fails."""

    pass


class DMGraphService:
    """
    Service for managing DM graph execution with LangGraph.

    This service handles the complete flow of DM interactions:
    1. Process user prompt and memory state
    2. Generate system prompt with context
    3. Call AI service with proper error handling
    4. Extract and format narrative response
    5. Update memory state for continuity
    """

    def __init__(self, config: Optional[DMGraphConfig] = None):
        self.config = config or DMGraphConfig()
        self.logger = get_logger(f"{__name__}.DMGraphService")

        # Initialize graph components
        self._graph = None
        self._memory_saver = MemorySaver() if LANGGRAPH_AVAILABLE else None
        self._is_initialized = False

        # Performance tracking
        self._execution_times: Dict[str, float] = {}

    async def initialize(self) -> bool:
        """Initialize the DM graph with all components."""
        try:
            if not LANGGRAPH_AVAILABLE:
                raise DMGraphError(
                    "LangGraph is not available. Install with: pip install langgraph"
                )

            if not ai_client.is_initialized():
                raise AIError("AI client is not initialized")

            # Build the graph
            self._graph = await self._build_graph()
            self._is_initialized = True

            self.logger.info("dm_graph_initialized")
            return True

        except Exception as e:
            self.logger.error("dm_graph_initialization_failed", error=str(e))
            return False

    async def _build_graph(self) -> Any:
        """Build the LangGraph workflow for DM interactions."""
        if not LANGGRAPH_AVAILABLE:
            raise DMGraphError("LangGraph not available")

        # Create the graph
        workflow = StateGraph(DMGraphState)

        # Add nodes
        workflow.add_node("process_prompt", self._process_prompt_node)
        workflow.add_node("compile_context", self._compile_context_node)
        workflow.add_node("ai_interaction", self._ai_interaction_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("update_memory", self._update_memory_node)
        workflow.add_node("handle_error", self._handle_error_node)

        # Define the flow - simple linear flow to avoid concurrent updates
        workflow.set_entry_point("process_prompt")

        # Linear flow with error handling at the end
        workflow.add_edge("process_prompt", "compile_context")
        workflow.add_edge("compile_context", "ai_interaction")
        workflow.add_edge("ai_interaction", "generate_response")
        workflow.add_edge("generate_response", "update_memory")
        workflow.add_edge("update_memory", "handle_error")
        workflow.add_edge("handle_error", END)

        # Compile the graph
        return workflow.compile(checkpointer=self._memory_saver)

    async def process_interaction(
        self,
        user_prompt: str,
        session_id: str,
        correlation_id: str,
        campaign_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a complete DM interaction using the LangGraph workflow.

        Args:
            user_prompt: The user's action or message
            session_id: Unique session identifier
            correlation_id: Correlation ID for tracing
            campaign_context: Additional campaign context

        Returns:
            Dict containing the narrative response and metadata
        """
        if not self._is_initialized or not self._graph:
            raise DMGraphError("DM graph is not initialized")

        start_time = time.time()

        try:
            # Load or create memory state
            memory_state = await self._load_memory_state(session_id)
            if campaign_context:
                memory_state.context.update(campaign_context)

            # Add user message to memory
            memory_state.add_message("user", user_prompt)

            # Create initial state
            initial_state = DMGraphState(
                user_prompt=user_prompt,
                memory_state=memory_state,
                system_prompt="",
                ai_response=None,
                narrative_response=None,
                error=None,
                correlation_id=correlation_id,
                context_messages=None,
                memory_context=None,
                processing_stage="start",
            )

            # Execute the graph with tracing
            with observability_service.trace_operation(
                operation_name="dm_graph_execution",
                session_id=session_id,
                correlation_id=correlation_id,
                prompt_length=len(user_prompt),
                memory_messages=len(memory_state.messages),
            ) as trace_id:
                # Run the graph
                result = await self._graph.ainvoke(
                    initial_state, config={"configurable": {"thread_id": session_id}}
                )

                execution_time = time.time() - start_time

                # Track performance
                if self.config.enable_performance_monitoring:
                    self._execution_times[correlation_id] = execution_time

                # Prepare response
                response = {
                    "narrative": result.get(
                        "narrative_response", "No response generated"
                    ),
                    "session_id": session_id,
                    "correlation_id": correlation_id,
                    "trace_id": trace_id,
                    "execution_time": execution_time,
                    "memory_state": {
                        "message_count": len(memory_state.messages),
                        "turn_count": memory_state.turn_count,
                        "scratchpad_items": len(memory_state.scratchpad),
                    },
                }

                # Add error information if present
                if result.get("error"):
                    response["error"] = result["error"]
                    response["status"] = "partial"

                self.logger.info(
                    "dm_interaction_completed",
                    session_id=session_id,
                    correlation_id=correlation_id,
                    execution_time=execution_time,
                    has_error=bool(result.get("error")),
                )

                return response

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"DM graph execution failed: {str(e)}"

            self.logger.error(
                "dm_interaction_failed",
                session_id=session_id,
                correlation_id=correlation_id,
                execution_time=execution_time,
                error=str(e),
            )

            # Return fallback response
            return {
                "narrative": self.config.fallback_responses.get(
                    "processing_error", "An error occurred processing your request."
                ),
                "session_id": session_id,
                "correlation_id": correlation_id,
                "execution_time": execution_time,
                "error": error_msg,
                "status": "error",
            }

    async def _process_prompt_node(self, state: DMGraphState) -> Dict[str, Any]:
        """Process the user prompt and validate input."""
        try:
            user_prompt = state["user_prompt"]

            # Basic prompt validation
            if not user_prompt or not user_prompt.strip():
                raise ValueError("User prompt cannot be empty")

            # Add to scratchpad for context
            state["memory_state"].add_to_scratchpad(
                f"User prompt: {user_prompt[:100]}..."
            )

            self.logger.debug(
                "prompt_processed",
                correlation_id=state["correlation_id"],
                prompt_length=len(user_prompt),
            )

            return {"processing_stage": "prompt_processed"}

        except Exception as e:
            self.logger.error(
                "prompt_processing_failed",
                correlation_id=state["correlation_id"],
                error=str(e),
            )
            return {"error": f"Prompt processing failed: {str(e)}", "processing_stage": "prompt_error"}

    async def _compile_context_node(self, state: DMGraphState) -> Dict[str, Any]:
        """Compile context including system prompt and memory using memory service."""
        try:
            correlation_id = state["correlation_id"]
            memory_state = state["memory_state"]
            user_prompt = state["user_prompt"]
            session_id = memory_state.session_id

            # Get system prompt
            try:
                system_prompt = prompt_manager.create_core_dm_prompt(
                    campaign_context=memory_state.context.get("campaign_name"),
                    player_count=4,  # Default, could be dynamic
                    campaign_tone=memory_state.context.get("tone", "balanced"),
                )
            except Exception as prompt_error:
                self.logger.warning(
                    "system_prompt_generation_failed",
                    correlation_id=correlation_id,
                    error=str(prompt_error),
                )
                # Use fallback system prompt
                system_prompt = self._get_fallback_system_prompt()

            # Prepare memory context using memory service
            memory_context = await memory_service.prepare_memory_context(
                session_id=session_id,
                user_prompt=user_prompt,
                correlation_id=correlation_id,
            )

            # Compile context messages from memory context
            context_messages = []

            # Add recent events from memory context
            for event in memory_context.recent_events:
                if event["type"] == "message":
                    context_messages.append(
                        {"role": event["role"], "content": event["content"]}
                    )
                elif event["type"] == "current_prompt":
                    # Current prompt will be added separately
                    pass

            # Add relevant memories as system context
            if memory_context.relevant_memories:
                memory_context_text = (
                    "Relevant context from previous interactions: "
                    + " ".join(
                        memory_context.relevant_memories[
                            :3
                        ]  # Limit to avoid token overflow
                    )
                )
                context_messages.append(
                    {"role": "system", "content": memory_context_text}
                )

            # Add character knowledge if available
            for char_name, knowledge_list in memory_context.character_knowledge.items():
                if knowledge_list:
                    char_context = f"Known information about {char_name}: " + " ".join(
                        knowledge_list[:2]
                    )
                    context_messages.append({"role": "system", "content": char_context})

            # Add world state if available
            if memory_context.world_state:
                world_context_parts = []
                for key, value in memory_context.world_state.items():
                    if value:
                        world_context_parts.append(f"{key}: {value}")
                if world_context_parts:
                    world_context_text = "Current world state: " + "; ".join(
                        world_context_parts
                    )
                    context_messages.append(
                        {"role": "system", "content": world_context_text}
                    )

            # Add scratchpad to context
            if memory_state.scratchpad:
                scratchpad_context = "Recent observations: " + "; ".join(
                    memory_state.scratchpad[-5:]
                )
                context_messages.append(
                    {"role": "system", "content": scratchpad_context}
                )

            # Add memory summary if available
            if memory_context.summary:
                context_messages.append(
                    {
                        "role": "system",
                        "content": f"Memory summary: {memory_context.summary}",
                    }
                )

            self.logger.debug(
                "context_compiled_with_memory_service",
                correlation_id=correlation_id,
                session_id=session_id,
                system_prompt_length=len(system_prompt),
                context_messages=len(context_messages),
                memory_token_count=memory_context.token_count,
                relevant_memories=len(memory_context.relevant_memories),
                recent_events=len(memory_context.recent_events),
            )

            return {
                "system_prompt": system_prompt,
                "context_messages": context_messages,
                "memory_context": memory_context,
                "processing_stage": "context_compiled",
            }

        except Exception as e:
            self.logger.error(
                "context_compilation_failed",
                correlation_id=state["correlation_id"],
                error=str(e),
            )
            return {"error": f"Context compilation failed: {str(e)}", "processing_stage": "context_error"}

    async def _ai_interaction_node(self, state: DMGraphState) -> Dict[str, Any]:
        """Handle AI interaction with proper error handling."""
        try:
            correlation_id = state["correlation_id"]
            system_prompt = state["system_prompt"]
            user_prompt = state["user_prompt"]

            # Prepare messages for AI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Call AI with tracing
            with observability_service.trace_operation(
                operation_name="ai_dm_response_generation",
                correlation_id=correlation_id,
                prompt_length=len(user_prompt),
                system_prompt_length=len(system_prompt),
            ) as trace_id:
                # Generate AI response
                ai_response = await ai_client.generate_chat(messages)

                self.logger.info(
                    "ai_response_generated",
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                    response_length=len(ai_response),
                )

                return {"ai_response": ai_response, "processing_stage": "ai_completed"}

        except Exception as e:
            error_msg = f"AI interaction failed: {str(e)}"
            self.logger.error(
                "ai_interaction_failed",
                correlation_id=state["correlation_id"],
                error=str(e),
            )
            return {"error": error_msg, "processing_stage": "ai_error"}

    async def _generate_response_node(self, state: DMGraphState) -> Dict[str, Any]:
        """Generate the final narrative response from AI response."""
        try:
            ai_response = state.get("ai_response", "")

            if not ai_response:
                raise ValueError("No AI response available for processing")

            # Extract narrative from AI response
            # This could involve parsing, cleaning, or formatting the AI response
            narrative_response = self._extract_narrative(ai_response)

            self.logger.debug(
                "narrative_generated",
                correlation_id=state["correlation_id"],
                ai_response_length=len(ai_response),
                narrative_length=len(narrative_response),
            )

            return {"narrative_response": narrative_response, "processing_stage": "response_generated"}

        except Exception as e:
            self.logger.error(
                "response_generation_failed",
                correlation_id=state["correlation_id"],
                error=str(e),
            )
            return {"error": f"Response generation failed: {str(e)}", "processing_stage": "response_error"}

    async def _update_memory_node(self, state: DMGraphState) -> Dict[str, Any]:
        """Update memory state with the interaction results using memory service."""
        try:
            memory_state = state["memory_state"]
            narrative_response = state.get("narrative_response", "")
            user_prompt = state["user_prompt"]
            correlation_id = state["correlation_id"]
            session_id = memory_state.session_id

            # Update memory using memory service
            await memory_service.update_memory_after_interaction(
                session_id=session_id,
                user_prompt=user_prompt,
                ai_response=narrative_response,
                correlation_id=correlation_id,
            )

            # Clear scratchpad for next interaction
            memory_state.clear_scratchpad()

            self.logger.debug(
                "memory_updated_with_service",
                correlation_id=correlation_id,
                session_id=session_id,
                user_prompt_length=len(user_prompt),
                ai_response_length=len(narrative_response),
            )

            return {"processing_stage": "memory_updated"}

        except Exception as e:
            self.logger.error(
                "memory_update_failed",
                correlation_id=state["correlation_id"],
                error=str(e),
            )
            return {"error": f"Memory update failed: {str(e)}", "processing_stage": "memory_error"}

    async def _handle_error_node(self, state: DMGraphState) -> Dict[str, Any]:
        """Handle errors and provide fallback responses."""
        error = state.get("error", "Unknown error")
        correlation_id = state["correlation_id"]

        self.logger.error(
            "dm_graph_error_handled", correlation_id=correlation_id, error=error
        )

        # Generate fallback response if no narrative exists
        if not state.get("narrative_response"):
            fallback_narrative = self.config.fallback_responses.get(
                "processing_error", "The DM encountered an issue processing your request."
            )
            return {"narrative_response": fallback_narrative, "processing_stage": "error_handled"}
        
        # If we already have a narrative, just mark as handled
        return {"processing_stage": "error_handled"}

    def _should_handle_error(self, state: DMGraphState) -> str:
        """Determine if error should be handled."""
        return "error" if state.get("error") else "continue"

    def _extract_narrative(self, ai_response: str) -> str:
        """Extract clean narrative from AI response."""
        # Basic cleaning - remove any system artifacts
        narrative = ai_response.strip()

        # Remove common AI prefixes
        prefixes_to_remove = ["As the DM,", "The DM says:", "DM:", "Dungeon Master:"]

        for prefix in prefixes_to_remove:
            if narrative.startswith(prefix):
                narrative = narrative[len(prefix) :].strip()
                break

        return narrative

    def _get_fallback_system_prompt(self) -> str:
        """Get a basic fallback system prompt."""
        return """You are an AI Dungeon Master for Dungeons & Dragons 5th Edition.
You create engaging, immersive roleplaying experiences. Respond to player actions
with narrative descriptions that advance the story and present interesting choices."""

    async def _load_memory_state(self, session_id: str) -> MemoryState:
        """Load memory state for a session."""
        # For now, create new memory state
        # In future, this would load from database
        return MemoryState(session_id=session_id)

    async def _persist_memory_state(self, memory_state: MemoryState) -> None:
        """Persist memory state."""
        # For now, just log
        # In future, this would save to database
        self.logger.debug(
            "memory_state_persisted",
            session_id=memory_state.session_id,
            message_count=len(memory_state.messages),
        )

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the DM graph service."""
        return {
            "status": "healthy" if self._is_initialized else "unhealthy",
            "langgraph_available": LANGGRAPH_AVAILABLE,
            "ai_client_initialized": ai_client.is_initialized(),
            "prompt_system_available": prompt_manager is not None,
            "execution_count": len(self._execution_times),
            "average_execution_time": sum(self._execution_times.values())
            / max(len(self._execution_times), 1),
        }

    def is_initialized(self) -> bool:
        """Check if the DM graph service is initialized."""
        return self._is_initialized


# Global DM graph service instance
dm_graph_service = DMGraphService()
