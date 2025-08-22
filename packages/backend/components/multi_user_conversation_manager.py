"""
Multi-User Conversation Manager Component for AI Dungeon Master.

This module provides comprehensive multi-user conversation handling with turn-taking
detection, conversation flow management, and inter-user communication support.

Features:
- Multi-stream audio mixing and routing
- Conversation turn-taking detection
- Group conversation context management
- Inter-user communication handling
- Real-time conversation state tracking
- Speaker priority and queue management
- Conversation flow optimization
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import (
    AudioMixConfiguration,
    MultiUserConversation,
    VoiceActivitySegment,
)

logger = get_logger(__name__)


@dataclass
class ConversationTurn:
    """Represents a single conversation turn."""

    turn_id: str
    speaker_id: str
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    text_content: str = ""
    audio_duration: float = 0.0
    turn_type: str = "speech"  # speech, interruption, backchannel, etc.
    confidence: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Get turn duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.utcnow() - self.start_time).total_seconds()


@dataclass
class SpeakerQueue:
    """Manages speaker turn-taking queue."""

    session_id: str
    max_wait_time: float = 30.0  # seconds
    priority_boost_duration: float = 5.0  # seconds for recent speakers

    _queue: deque = field(default_factory=deque)
    _active_speakers: Set[str] = field(default_factory=set)
    _last_speak_time: Dict[str, datetime] = field(default_factory=dict)
    _priority_scores: Dict[str, float] = field(default_factory=dict)

    def add_speaker(self, speaker_id: str, priority: float = 1.0) -> None:
        """Add speaker to queue with priority."""
        if speaker_id not in [s[0] for s in self._queue]:
            self._priority_scores[speaker_id] = priority
            self._queue.append((speaker_id, datetime.utcnow(), priority))
            self._sort_queue()

    def remove_speaker(self, speaker_id: str) -> None:
        """Remove speaker from queue."""
        self._queue = deque([(s, t, p) for s, t, p in self._queue if s != speaker_id])
        self._active_speakers.discard(speaker_id)

    def get_next_speaker(self) -> Optional[str]:
        """Get next speaker from queue."""
        if not self._queue:
            return None

        # Find speaker with highest priority who hasn't spoken recently
        current_time = datetime.utcnow()

        for speaker_id, add_time, base_priority in self._queue:
            if current_time - add_time > timedelta(seconds=self.max_wait_time):
                # Remove expired requests
                self.remove_speaker(speaker_id)
                continue

            # Calculate effective priority
            effective_priority = self._calculate_effective_priority(
                speaker_id, base_priority, current_time
            )

            # Check if speaker is available
            if speaker_id not in self._active_speakers:
                return speaker_id

        return None

    def _calculate_effective_priority(
        self, speaker_id: str, base_priority: float, current_time: datetime
    ) -> float:
        """Calculate effective priority for speaker."""
        effective_priority = base_priority

        # Boost priority for speakers who haven't spoken recently
        if speaker_id in self._last_speak_time:
            time_since_last_speech = (
                current_time - self._last_speak_time[speaker_id]
            ).total_seconds()
            if time_since_last_speech > self.priority_boost_duration:
                effective_priority *= 1 + time_since_last_speech / 60.0  # Gradual boost

        return effective_priority

    def _sort_queue(self) -> None:
        """Sort queue by effective priority."""
        current_time = datetime.utcnow()

        def get_effective_priority(item):
            speaker_id, add_time, base_priority = item
            return self._calculate_effective_priority(
                speaker_id, base_priority, current_time
            )

        self._queue = deque(
            sorted(self._queue, key=get_effective_priority, reverse=True)
        )

    def mark_speaker_active(self, speaker_id: str) -> None:
        """Mark speaker as currently active."""
        self._active_speakers.add(speaker_id)

    def mark_speaker_inactive(self, speaker_id: str) -> None:
        """Mark speaker as no longer active."""
        self._active_speakers.discard(speaker_id)
        self._last_speak_time[speaker_id] = datetime.utcnow()

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "queued_speakers": len(self._queue),
            "active_speakers": len(self._active_speakers),
            "queue": [
                (s, (datetime.utcnow() - t).total_seconds()) for s, t, p in self._queue
            ],
        }


class MultiUserConversationManager:
    """
    Manages multi-user conversations with turn-taking and flow control.

    Features:
    - Multi-stream audio mixing and routing
    - Conversation turn-taking detection
    - Group conversation context management
    - Inter-user communication handling
    - Real-time conversation state tracking
    - Speaker priority and queue management
    - Conversation flow optimization
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Active conversations
        self.active_conversations: Dict[str, MultiUserConversation] = {}

        # Speaker queues for turn-taking
        self.speaker_queues: Dict[str, SpeakerQueue] = {}

        # Audio mixing configurations
        self.mix_configs: Dict[str, AudioMixConfiguration] = {}

        # Conversation statistics
        self.conversation_stats = {
            "total_conversations": 0,
            "total_turns": 0,
            "average_turn_duration": 0.0,
            "interruption_rate": 0.0,
            "turn_taking_efficiency": 0.0,
        }

        # Configuration
        self.max_concurrent_conversations = self.config.get(
            "max_concurrent_conversations", 10
        )
        self.max_speakers_per_conversation = self.config.get(
            "max_speakers_per_conversation", 8
        )
        self.turn_timeout = self.config.get("turn_timeout", 30.0)
        self.overlap_threshold = self.config.get("overlap_threshold", 0.5)  # seconds

        # Background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info("multi_user_conversation_manager_initialized")

    async def start_manager(self) -> None:
        """Start the conversation manager."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("multi_user_conversation_manager_started")

    async def stop_manager(self) -> None:
        """Stop the conversation manager."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        logger.info("multi_user_conversation_manager_stopped")

    async def create_conversation(
        self,
        session_id: str,
        initial_speakers: List[str],
        conversation_type: str = "group",
        correlation_id: Optional[str] = None,
    ) -> Optional[MultiUserConversation]:
        """
        Create a new multi-user conversation.

        Args:
            session_id: Voice session identifier
            initial_speakers: List of initial speaker user IDs
            conversation_type: Type of conversation
            correlation_id: Correlation ID for tracing

        Returns:
            MultiUserConversation if created successfully
        """
        try:
            with observability_service.trace_operation(
                operation_name="create_multi_user_conversation",
                session_id=session_id,
                speaker_count=len(initial_speakers),
                correlation_id=correlation_id,
            ) as trace_id:
                # Check limits
                if len(self.active_conversations) >= self.max_concurrent_conversations:
                    logger.warning(
                        "max_concurrent_conversations_exceeded",
                        session_id=session_id,
                        current_count=len(self.active_conversations),
                        correlation_id=correlation_id,
                    )
                    return None

                if len(initial_speakers) > self.max_speakers_per_conversation:
                    logger.warning(
                        "max_speakers_per_conversation_exceeded",
                        session_id=session_id,
                        speaker_count=len(initial_speakers),
                        correlation_id=correlation_id,
                    )
                    return None

                # Create conversation
                conversation = MultiUserConversation(
                    conversation_id=f"conv_{session_id}_{int(time.time() * 1000)}",
                    session_id=session_id,
                    active_speakers=initial_speakers.copy(),
                    total_speakers=len(initial_speakers),
                )

                # Create speaker queue
                speaker_queue = SpeakerQueue(session_id=session_id)
                for speaker_id in initial_speakers:
                    speaker_queue.add_speaker(speaker_id)

                # Create audio mixing configuration
                mix_config = AudioMixConfiguration(
                    mix_id=f"mix_{session_id}",
                    session_id=session_id,
                    input_streams=[
                        f"stream_{speaker_id}" for speaker_id in initial_speakers
                    ],
                    output_stream=f"mixed_{session_id}",
                )

                # Store everything
                self.active_conversations[session_id] = conversation
                self.speaker_queues[session_id] = speaker_queue
                self.mix_configs[session_id] = mix_config

                # Update statistics
                self.conversation_stats["total_conversations"] += 1

                logger.info(
                    "multi_user_conversation_created",
                    conversation_id=conversation.conversation_id,
                    session_id=session_id,
                    speaker_count=len(initial_speakers),
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                )

                return conversation

        except Exception as e:
            logger.error(
                "multi_user_conversation_creation_failed",
                session_id=session_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return None

    async def process_voice_activity(
        self,
        session_id: str,
        speaker_id: str,
        audio_segment: bytes,
        start_time: datetime,
        end_time: datetime,
        confidence: float = 0.0,
        correlation_id: Optional[str] = None,
    ) -> Optional[VoiceActivitySegment]:
        """
        Process voice activity in a multi-user conversation.

        Args:
            session_id: Voice session identifier
            speaker_id: Speaker user ID
            audio_segment: Audio data
            start_time: Activity start time
            end_time: Activity end time
            confidence: Voice activity confidence
            correlation_id: Correlation ID for tracing

        Returns:
            VoiceActivitySegment if processed successfully
        """
        try:
            if session_id not in self.active_conversations:
                logger.warning(
                    "conversation_not_found_for_activity",
                    session_id=session_id,
                    speaker_id=speaker_id,
                    correlation_id=correlation_id,
                )
                return None

            conversation = self.active_conversations[session_id]
            speaker_queue = self.speaker_queues.get(session_id)

            # Calculate segment duration
            duration = (end_time - start_time).total_seconds()

            # Check for speaker overlaps
            overlap_detected = self._detect_speaker_overlap(
                session_id, speaker_id, start_time, end_time
            )

            # Create activity segment
            segment = VoiceActivitySegment(
                segment_id=f"segment_{session_id}_{speaker_id}_{int(time.time() * 1000)}",
                session_id=session_id,
                speaker_id=speaker_id,
                start_time=start_time,
                end_time=end_time,
                confidence=confidence,
                energy_level=0.8,  # Would calculate from audio
                noise_level=0.1,  # Would calculate from audio
                overlap_detected=overlap_detected,
                speaker_confidence=confidence,
                duration=duration,
            )

            # Update conversation
            conversation.speaker_segments.append(segment)
            conversation.total_turns += 1

            # Update speaker queue
            if speaker_queue:
                speaker_queue.mark_speaker_active(speaker_id)

            # Add to conversation flow
            conversation.conversation_flow.append(
                {
                    "speaker_id": speaker_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": duration,
                    "confidence": confidence,
                    "overlap_detected": overlap_detected,
                }
            )

            # Update turn-taking events
            conversation.turn_taking_events.append(
                {
                    "event_type": "speech_start"
                    if not overlap_detected
                    else "interruption",
                    "speaker_id": speaker_id,
                    "timestamp": start_time.isoformat(),
                    "duration": duration,
                }
            )

            # Update statistics
            self._update_conversation_stats(conversation, segment)

            logger.info(
                "voice_activity_processed",
                session_id=session_id,
                speaker_id=speaker_id,
                duration=duration,
                confidence=confidence,
                overlap_detected=overlap_detected,
                correlation_id=correlation_id,
            )

            return segment

        except Exception as e:
            logger.error(
                "voice_activity_processing_failed",
                session_id=session_id,
                speaker_id=speaker_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return None

    async def get_next_speaker(
        self,
        session_id: str,
        requesting_speakers: List[str],
        correlation_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get the next speaker for turn-taking.

        Args:
            session_id: Voice session identifier
            requesting_speakers: List of speakers requesting to speak
            correlation_id: Correlation ID for tracing

        Returns:
            Next speaker ID or None
        """
        try:
            if session_id not in self.speaker_queues:
                logger.warning(
                    "speaker_queue_not_found",
                    session_id=session_id,
                    correlation_id=correlation_id,
                )
                return None

            speaker_queue = self.speaker_queues[session_id]

            # Add requesting speakers to queue
            for speaker_id in requesting_speakers:
                if speaker_id not in [s[0] for s in speaker_queue._queue]:
                    speaker_queue.add_speaker(speaker_id)

            # Get next speaker
            next_speaker = speaker_queue.get_next_speaker()

            if next_speaker:
                logger.info(
                    "next_speaker_selected",
                    session_id=session_id,
                    next_speaker=next_speaker,
                    queue_size=len(speaker_queue._queue),
                    correlation_id=correlation_id,
                )

            return next_speaker

        except Exception as e:
            logger.error(
                "next_speaker_selection_failed",
                session_id=session_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return None

    async def end_speaker_turn(
        self, session_id: str, speaker_id: str, correlation_id: Optional[str] = None
    ) -> bool:
        """
        End a speaker's turn and update conversation state.

        Args:
            session_id: Voice session identifier
            speaker_id: Speaker whose turn is ending
            correlation_id: Correlation ID for tracing

        Returns:
            True if turn ended successfully
        """
        try:
            if session_id not in self.active_conversations:
                return False

            conversation = self.active_conversations[session_id]
            speaker_queue = self.speaker_queues.get(session_id)

            # Mark speaker as inactive
            if speaker_queue:
                speaker_queue.mark_speaker_inactive(speaker_id)

            # Update conversation flow
            conversation.turn_taking_events.append(
                {
                    "event_type": "speech_end",
                    "speaker_id": speaker_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            logger.info(
                "speaker_turn_ended",
                session_id=session_id,
                speaker_id=speaker_id,
                correlation_id=correlation_id,
            )

            return True

        except Exception as e:
            logger.error(
                "speaker_turn_end_failed",
                session_id=session_id,
                speaker_id=speaker_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return False

    def _detect_speaker_overlap(
        self, session_id: str, speaker_id: str, start_time: datetime, end_time: datetime
    ) -> bool:
        """Detect if speaker is overlapping with others."""
        try:
            conversation = self.active_conversations.get(session_id)
            if not conversation:
                return False

            # Check recent segments for overlaps
            recent_segments = [
                seg
                for seg in conversation.speaker_segments[-10:]  # Last 10 segments
                if seg.speaker_id != speaker_id and seg.end_time > start_time
            ]

            # Check if any recent segment overlaps with current
            for segment in recent_segments:
                if segment.start_time < end_time and segment.end_time > start_time:
                    overlap_duration = min(end_time, segment.end_time) - max(
                        start_time, segment.start_time
                    )
                    if overlap_duration.total_seconds() > self.overlap_threshold:
                        return True

            return False

        except Exception as e:
            logger.warning("overlap_detection_failed", error=str(e))
            return False

    def _update_conversation_stats(
        self, conversation: MultiUserConversation, segment: VoiceActivitySegment
    ) -> None:
        """Update conversation statistics."""
        try:
            # Update total turns
            self.conversation_stats["total_turns"] += 1

            # Update average turn duration
            total_duration = sum(
                seg.duration
                for seg in conversation.speaker_segments
                if seg.duration is not None
            )
            avg_duration = total_duration / len(conversation.speaker_segments)
            self.conversation_stats["average_turn_duration"] = avg_duration

            # Update interruption rate
            interruptions = sum(
                1 for seg in conversation.speaker_segments if seg.overlap_detected
            )
            total_segments = len(conversation.speaker_segments)
            if total_segments > 0:
                self.conversation_stats["interruption_rate"] = (
                    interruptions / total_segments
                )

            # Update turn-taking efficiency
            if conversation.turn_taking_events:
                speech_events = [
                    e
                    for e in conversation.turn_taking_events
                    if e["event_type"] == "speech_start"
                ]
                if speech_events:
                    # Simple efficiency metric
                    efficiency = 1.0 - (interruptions / len(speech_events))
                    self.conversation_stats["turn_taking_efficiency"] = max(
                        0.0, efficiency
                    )

        except Exception as e:
            logger.warning("conversation_stats_update_failed", error=str(e))

    async def get_conversation_status(
        self, session_id: str, correlation_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get current conversation status."""
        try:
            if session_id not in self.active_conversations:
                return None

            conversation = self.active_conversations[session_id]
            speaker_queue = self.speaker_queues.get(session_id)

            status = {
                "conversation_id": conversation.conversation_id,
                "active_speakers": conversation.active_speakers.copy(),
                "total_turns": conversation.total_turns,
                "total_speakers": conversation.total_speakers,
                "dominant_speaker": conversation.dominant_speaker,
                "started_at": conversation.started_at.isoformat(),
                "last_activity": conversation.last_activity.isoformat(),
            }

            if speaker_queue:
                status["speaker_queue"] = speaker_queue.get_queue_status()

            return status

        except Exception as e:
            logger.error(
                "conversation_status_retrieval_failed",
                session_id=session_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return None

    async def end_conversation(
        self,
        session_id: str,
        reason: str = "completed",
        correlation_id: Optional[str] = None,
    ) -> bool:
        """End a multi-user conversation."""
        try:
            if session_id not in self.active_conversations:
                return False

            conversation = self.active_conversations[session_id]

            # Clean up conversation
            if session_id in self.speaker_queues:
                del self.speaker_queues[session_id]

            if session_id in self.mix_configs:
                del self.mix_configs[session_id]

            # Move to completed conversations (if we want to keep history)
            # For now, just remove it
            del self.active_conversations[session_id]

            logger.info(
                "multi_user_conversation_ended",
                conversation_id=conversation.conversation_id,
                session_id=session_id,
                reason=reason,
                total_turns=conversation.total_turns,
                correlation_id=correlation_id,
            )

            return True

        except Exception as e:
            logger.error(
                "conversation_end_failed",
                session_id=session_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return False

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(30)  # Monitor every 30 seconds

                # Check for stale conversations
                current_time = datetime.utcnow()
                for session_id, conversation in list(self.active_conversations.items()):
                    if current_time - conversation.last_activity > timedelta(minutes=5):
                        logger.warning(
                            "conversation_inactive_detected",
                            session_id=session_id,
                            inactive_minutes=5,
                        )

            except Exception as e:
                logger.error("monitoring_loop_error", error=str(e))

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes

                # Clean up expired conversations
                current_time = datetime.utcnow()
                expired_sessions = []

                for session_id, conversation in self.active_conversations.items():
                    if current_time - conversation.started_at > timedelta(hours=2):
                        expired_sessions.append(session_id)

                for session_id in expired_sessions:
                    await self.end_conversation(session_id, "expired")

                if expired_sessions:
                    logger.info(
                        "expired_conversations_cleaned", count=len(expired_sessions)
                    )

            except Exception as e:
                logger.error("cleanup_loop_error", error=str(e))

    def get_conversation_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        return {
            **self.conversation_stats,
            "active_conversations": len(self.active_conversations),
            "total_speaker_queues": len(self.speaker_queues),
            "total_mix_configs": len(self.mix_configs),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the conversation manager."""
        total_conversations = len(self.active_conversations)
        avg_turns_per_conversation = 0.0

        if total_conversations > 0:
            total_turns = sum(
                conv.total_turns for conv in self.active_conversations.values()
            )
            avg_turns_per_conversation = total_turns / total_conversations

        return {
            "status": "healthy"
            if total_conversations <= self.max_concurrent_conversations
            else "degraded",
            "active_conversations": total_conversations,
            "max_concurrent_conversations": self.max_concurrent_conversations,
            "average_turns_per_conversation": avg_turns_per_conversation,
            "total_turns_today": self.conversation_stats["total_turns"],
            "interruption_rate": self.conversation_stats["interruption_rate"],
            "turn_taking_efficiency": self.conversation_stats["turn_taking_efficiency"],
            "background_tasks": {
                "monitoring_active": self._monitoring_task is not None
                and not self._monitoring_task.done(),
                "cleanup_active": self._cleanup_task is not None
                and not self._cleanup_task.done(),
            },
        }


# Global multi-user conversation manager instance
multi_user_conversation_manager = MultiUserConversationManager()
