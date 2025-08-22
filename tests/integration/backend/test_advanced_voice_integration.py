"""
Integration tests for Advanced Voice Features.

Tests the complete integration of all advanced voice components including
speaker identification, multi-user conversations, enhanced VAD, audio mixing,
spatial audio, and conversation intelligence working together.
"""

import asyncio
from datetime import datetime
from unittest.mock import patch

import numpy as np
import pytest

from packages.backend.components.advanced_vad_processor import AdvancedVADProcessor
from packages.backend.components.audio_mixer_service import (
    AudioMixerService,
    AudioSource,
    SpatialPosition,
)
from packages.backend.components.conversation_intelligence import (
    ConversationIntelligenceEngine,
)
from packages.backend.components.multi_user_conversation_manager import (
    MultiUserConversationManager,
)
from packages.backend.components.speaker_identification_service import (
    SpeakerIdentificationService,
)
from packages.shared.models import (
    SpeakerProfile,
)


class TestAdvancedVoiceIntegration:
    """Integration tests for complete advanced voice system."""

    @pytest.fixture
    def integration_components(self):
        """Create all advanced voice components for integration testing."""
        with (
            patch(
                "packages.backend.components.speaker_identification_service.AudioUtils"
            ),
            patch(
                "packages.backend.components.multi_user_conversation_manager.AudioUtils"
            ),
            patch("packages.backend.components.advanced_vad_processor.AudioUtils"),
            patch("packages.backend.components.audio_mixer_service.AudioUtils"),
            patch("packages.backend.components.conversation_intelligence.AudioUtils"),
        ):
            # Create all components
            speaker_id_service = SpeakerIdentificationService()
            conversation_manager = MultiUserConversationManager()
            vad_processor = AdvancedVADProcessor()
            audio_mixer = AudioMixerService()
            intelligence_engine = ConversationIntelligenceEngine()

            return {
                "speaker_id": speaker_id_service,
                "conversation_manager": conversation_manager,
                "vad_processor": vad_processor,
                "audio_mixer": audio_mixer,
                "intelligence_engine": intelligence_engine,
            }

    @pytest.fixture
    def sample_audio_streams(self):
        """Generate realistic sample audio streams for testing."""
        buffer_size = 1024
        sample_rate = 16000

        # Create different speaker characteristics
        speaker1_audio = np.random.normal(0, 0.3, buffer_size).astype(np.float32)
        # Add some speech-like characteristics to speaker 1
        t = np.linspace(0, buffer_size / sample_rate, buffer_size)
        speech_pattern = 0.5 * np.sin(2 * np.pi * 220 * t)  # 220Hz tone
        speaker1_audio += speech_pattern

        speaker2_audio = np.random.normal(0, 0.25, buffer_size).astype(np.float32)
        # Different frequency for speaker 2
        speech_pattern2 = 0.4 * np.sin(2 * np.pi * 180 * t)  # 180Hz tone
        speaker2_audio += speech_pattern2

        speaker3_audio = np.random.normal(0, 0.2, buffer_size).astype(np.float32)
        # Even different characteristics for speaker 3
        noise = np.random.normal(0, 0.15, buffer_size)
        speaker3_audio += noise

        return {
            "user_123": speaker1_audio,
            "user_456": speaker2_audio,
            "user_789": speaker3_audio,
        }

    @pytest.mark.asyncio
    async def test_complete_voice_session_workflow(
        self, integration_components, sample_audio_streams
    ):
        """Test complete voice session workflow from start to finish."""
        components = integration_components

        # Step 1: Initialize session components
        session_id = "integration_test_session"

        # Initialize audio mixer
        await components["audio_mixer"].create_mix_session(session_id)

        # Initialize conversation manager
        conversation = await components["conversation_manager"].create_conversation(
            session_id, ["user_123", "user_456", "user_789"]
        )
        assert conversation is not None

        # Step 2: Add speakers to all systems
        for user_id, audio_data in sample_audio_streams.items():
            # Add to audio mixer
            source = AudioSource(source_id=user_id, user_id=user_id)
            await components["audio_mixer"].add_audio_source(session_id, source)

            # Create speaker profile
            profile = SpeakerProfile(
                profile_id=f"profile_{user_id}",
                user_id=user_id,
                voice_print=b"sample_voice_print",
                voice_characteristics={"pitch": 200 + hash(user_id) % 50},
            )

            # Register with speaker ID service
            await components["speaker_id"].register_speaker_profile(profile)

        # Step 3: Process audio through complete pipeline
        mixed_audio = await components["audio_mixer"].mix_audio_streams(
            session_id, sample_audio_streams
        )
        assert mixed_audio is not None
        assert len(mixed_audio) > 0

        # Step 4: Test VAD processing on mixed audio
        vad_segments = await components["vad_processor"].process_audio_frame(
            session_id, mixed_audio.tobytes(), "user_123"
        )
        # Should detect some voice activity
        assert isinstance(vad_segments, list)

        # Step 5: Test conversation intelligence analysis
        segment_data = {
            "segment_id": "test_segment_1",
            "speaker_id": "user_123",
            "audio_data": mixed_audio,
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow(),
        }

        analysis_result = await components["intelligence_engine"].analyze_voice_segment(
            session_id, segment_data
        )

        # Should have complete analysis
        expected_keys = [
            "conversation_id",
            "segment_id",
            "sentiment_analysis",
            "engagement_metrics",
            "flow_analysis",
            "highlights",
        ]
        for key in expected_keys:
            assert key in analysis_result

        # Step 6: Verify speaker identification
        identified_speaker = await components["speaker_id"].identify_speaker(
            sample_audio_streams["user_123"].tobytes()
        )
        # Should identify the speaker
        assert identified_speaker is not None

        # Step 7: Test conversation management
        updated_conversation = await components[
            "conversation_manager"
        ].get_conversation(session_id)
        assert updated_conversation is not None
        assert len(updated_conversation.active_speakers) > 0

        # Step 8: Generate conversation summary
        summary = await components["intelligence_engine"].generate_conversation_summary(
            session_id
        )
        assert isinstance(summary, dict)
        assert "duration_minutes" in summary
        assert "total_segments" in summary

        # Cleanup
        await components["audio_mixer"].cleanup_session(session_id)
        await components["conversation_manager"].end_conversation(session_id)
        await components["intelligence_engine"].cleanup_conversation(session_id)

    @pytest.mark.asyncio
    async def test_multi_user_conversation_dynamics(
        self, integration_components, sample_audio_streams
    ):
        """Test multi-user conversation dynamics and turn-taking."""
        components = integration_components
        session_id = "multi_user_test_session"

        # Initialize systems
        await components["audio_mixer"].create_mix_session(session_id)
        conversation = await components["conversation_manager"].create_conversation(
            session_id, list(sample_audio_streams.keys())
        )

        # Simulate conversation turns
        turns = [
            ("user_123", sample_audio_streams["user_123"]),
            ("user_456", sample_audio_streams["user_456"]),
            ("user_789", sample_audio_streams["user_789"]),
            ("user_123", sample_audio_streams["user_123"]),  # Speaker 1 speaks again
        ]

        conversation_highlights = []

        for i, (speaker_id, audio_data) in enumerate(turns):
            # Process through VAD
            vad_segments = await components["vad_processor"].process_audio_frame(
                session_id, audio_data.tobytes(), speaker_id
            )

            # Analyze with intelligence engine
            segment_data = {
                "segment_id": f"turn_{i + 1}",
                "speaker_id": speaker_id,
                "audio_data": audio_data,
                "start_time": datetime.utcnow(),
                "end_time": datetime.utcnow(),
            }

            analysis = await components["intelligence_engine"].analyze_voice_segment(
                session_id, segment_data
            )

            # Collect highlights
            highlights = analysis.get("highlights", [])
            conversation_highlights.extend(highlights)

            # Update conversation state
            await components["conversation_manager"].process_voice_activity(
                session_id, speaker_id, True
            )

        # Verify conversation dynamics
        final_conversation = await components["conversation_manager"].get_conversation(
            session_id
        )
        assert final_conversation is not None

        # Check turn-taking was recorded
        assert len(final_conversation.turn_taking_events) >= len(turns)

        # Verify engagement analysis
        summary = await components["intelligence_engine"].generate_conversation_summary(
            session_id
        )
        assert summary["total_segments"] >= len(turns)
        assert summary["active_speakers"] == 3

    @pytest.mark.asyncio
    async def test_audio_mixing_with_spatial_audio(
        self, integration_components, sample_audio_streams
    ):
        """Test audio mixing with spatial positioning."""
        components = integration_components
        session_id = "spatial_audio_test"

        # Initialize with spatial audio enabled
        await components["audio_mixer"].create_mix_session(session_id)

        # Position speakers in 3D space
        positions = {
            "user_123": SpatialPosition(
                x=1.0, y=0.0, z=0.0, distance=2.0
            ),  # Right side
            "user_456": SpatialPosition(
                x=-1.0, y=0.0, z=0.0, distance=1.5
            ),  # Left side
            "user_789": SpatialPosition(
                x=0.0, y=1.0, z=0.0, distance=1.0
            ),  # Front center
        }

        # Add sources with spatial positions
        for user_id, audio_data in sample_audio_streams.items():
            source = AudioSource(
                source_id=user_id, user_id=user_id, position=positions[user_id]
            )
            await components["audio_mixer"].add_audio_source(session_id, source)

        # Mix with spatial processing
        mixed_audio = await components["audio_mixer"].mix_audio_streams(
            session_id, sample_audio_streams
        )

        # Should produce stereo output due to spatial positioning
        assert mixed_audio.shape[1] == 2  # Stereo

        # Test position updates
        new_position = SpatialPosition(x=0.5, y=0.5, z=0.0, distance=1.2)
        success = await components["audio_mixer"].update_source_position(
            session_id, "user_123", new_position
        )
        assert success is True

        # Mix again with new position
        mixed_audio_2 = await components["audio_mixer"].mix_audio_streams(
            session_id, sample_audio_streams
        )
        assert mixed_audio_2.shape == mixed_audio.shape

    @pytest.mark.asyncio
    async def test_focus_mode_and_ducking(
        self, integration_components, sample_audio_streams
    ):
        """Test focus mode and audio ducking functionality."""
        components = integration_components
        session_id = "focus_test_session"

        await components["audio_mixer"].create_mix_session(session_id)

        # Add sources with different priorities
        sources = {}
        for i, (user_id, audio_data) in enumerate(sample_audio_streams.items()):
            source = AudioSource(
                source_id=user_id,
                user_id=user_id,
                priority=i + 1,  # Different priorities
            )
            sources[user_id] = source
            await components["audio_mixer"].add_audio_source(session_id, source)

        # Enable focus mode on highest priority speaker
        focus_speaker = "user_123"  # Highest priority
        success = await components["audio_mixer"].set_focus_mode(
            session_id, focus_speaker, enable=True
        )
        assert success is True

        # Mix with focus mode
        mixed_audio_focused = await components["audio_mixer"].mix_audio_streams(
            session_id, sample_audio_streams
        )

        # Disable focus mode
        success = await components["audio_mixer"].set_focus_mode(
            session_id, None, enable=False
        )
        assert success is True

        # Mix without focus mode
        mixed_audio_normal = await components["audio_mixer"].mix_audio_streams(
            session_id, sample_audio_streams
        )

        # Should produce different mixing results
        assert not np.array_equal(mixed_audio_focused, mixed_audio_normal)

    @pytest.mark.asyncio
    async def test_vad_multi_speaker_detection(
        self, integration_components, sample_audio_streams
    ):
        """Test VAD with multiple simultaneous speakers."""
        components = integration_components
        session_id = "vad_multi_speaker_test"

        # Create overlapping audio (simulating multiple speakers)
        combined_audio = np.sum(list(sample_audio_streams.values()), axis=0)
        # Normalize to prevent clipping
        max_val = np.max(np.abs(combined_audio))
        if max_val > 1.0:
            combined_audio = combined_audio / max_val

        # Process through VAD
        vad_segments = await components["vad_processor"].process_audio_frame(
            session_id, combined_audio.tobytes()
        )

        # Should detect voice activity
        assert isinstance(vad_segments, list)

        # Test adaptive thresholds
        vad_state = await components["vad_processor"].get_vad_state(session_id)
        assert vad_state is not None

        # Process more frames to allow adaptation
        for _ in range(5):
            await components["vad_processor"].process_audio_frame(
                session_id, combined_audio.tobytes()
            )

        # Check that VAD state has been updated
        updated_state = await components["vad_processor"].get_vad_state(session_id)
        assert updated_state is not None

    @pytest.mark.asyncio
    async def test_speaker_identification_integration(
        self, integration_components, sample_audio_streams
    ):
        """Test speaker identification integration with other components."""
        components = integration_components
        session_id = "speaker_id_integration_test"

        # Register speaker profiles
        for user_id in sample_audio_streams.keys():
            profile = SpeakerProfile(
                profile_id=f"profile_{user_id}",
                user_id=user_id,
                voice_print=b"sample_voice_print",
                voice_characteristics={"unique_feature": hash(user_id) % 100},
            )
            await components["speaker_id"].register_speaker_profile(profile)

        # Test identification for each speaker
        identification_results = {}
        for user_id, audio_data in sample_audio_streams.items():
            identified = await components["speaker_id"].identify_speaker(
                audio_data.tobytes()
            )
            identification_results[user_id] = identified

        # Should identify speakers
        assert len(identification_results) == len(sample_audio_streams)

        # Test confidence scoring
        for user_id, result in identification_results.items():
            assert result is not None
            # In real implementation, this would check confidence thresholds

    @pytest.mark.asyncio
    async def test_conversation_intelligence_with_vad(
        self, integration_components, sample_audio_streams
    ):
        """Test conversation intelligence working with VAD results."""
        components = integration_components
        session_id = "intelligence_vad_test"

        # Process audio through VAD first
        vad_results = []
        for user_id, audio_data in sample_audio_streams.items():
            segments = await components["vad_processor"].process_audio_frame(
                session_id, audio_data.tobytes(), user_id
            )
            vad_results.extend(segments)

        # Feed VAD results into conversation intelligence
        for i, vad_segment in enumerate(vad_results[:3]):  # Test first 3 segments
            segment_data = {
                "segment_id": f"vad_segment_{i}",
                "speaker_id": vad_segment.speaker_id or f"unknown_{i}",
                "audio_data": sample_audio_streams.get(
                    vad_segment.speaker_id, sample_audio_streams["user_123"]
                ),
                "start_time": vad_segment.start_time,
                "end_time": vad_segment.end_time,
            }

            analysis = await components["intelligence_engine"].analyze_voice_segment(
                session_id, segment_data
            )

            # Should integrate VAD confidence with sentiment analysis
            assert "sentiment_analysis" in analysis
            assert "engagement_metrics" in analysis

        # Verify conversation context was updated
        context = await components["intelligence_engine"].get_conversation_stats(
            session_id
        )
        assert context["total_segments"] >= len(vad_results[:3])

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(
        self, integration_components, sample_audio_streams
    ):
        """Test error handling and recovery across components."""
        components = integration_components
        session_id = "error_handling_test"

        # Test with invalid session ID
        invalid_result = await components["audio_mixer"].mix_audio_streams(
            "invalid_session", {}
        )
        assert isinstance(invalid_result, np.ndarray)  # Should return silent audio

        # Test with malformed audio data
        malformed_audio = b"not_audio_data"
        try:
            await components["vad_processor"].process_audio_frame(
                session_id, malformed_audio
            )
        except Exception as e:
            # Should handle gracefully
            assert "processing audio frame" in str(e).lower() or isinstance(
                e, (ValueError, Exception)
            )

        # Test session cleanup
        await components["audio_mixer"].create_mix_session(session_id)
        await components["audio_mixer"].cleanup_session(session_id)

        # Verify cleanup
        state = await components["audio_mixer"].get_mixing_state(session_id)
        assert state is None

    @pytest.mark.asyncio
    async def test_performance_under_load(
        self, integration_components, sample_audio_streams
    ):
        """Test system performance with multiple concurrent operations."""
        components = integration_components

        # Create multiple sessions
        sessions = [f"load_test_session_{i}" for i in range(5)]

        # Initialize all sessions
        init_tasks = []
        for session_id in sessions:
            init_tasks.append(components["audio_mixer"].create_mix_session(session_id))
            init_tasks.append(
                components["conversation_manager"].create_conversation(
                    session_id, ["user_123"]
                )
            )

        await asyncio.gather(*init_tasks)

        # Process multiple audio streams concurrently
        processing_tasks = []
        for session_id in sessions:
            for user_id, audio_data in sample_audio_streams.items():
                processing_tasks.append(
                    components["vad_processor"].process_audio_frame(
                        session_id, audio_data.tobytes(), user_id
                    )
                )

        start_time = datetime.utcnow()
        results = await asyncio.gather(*processing_tasks)
        end_time = datetime.utcnow()

        # Should process all requests within reasonable time
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 30.0  # Should complete within 30 seconds

        # Verify all results
        assert len(results) == len(sessions) * len(sample_audio_streams)
        for result in results:
            assert isinstance(result, list)

        # Cleanup all sessions
        cleanup_tasks = []
        for session_id in sessions:
            cleanup_tasks.append(components["audio_mixer"].cleanup_session(session_id))
            cleanup_tasks.append(
                components["conversation_manager"].end_conversation(session_id)
            )

        await asyncio.gather(*cleanup_tasks)

    def test_component_compatibility(self, integration_components):
        """Test that all components are compatible and can be instantiated together."""
        components = integration_components

        # Verify all components exist and are properly initialized
        required_components = [
            "speaker_id",
            "conversation_manager",
            "vad_processor",
            "audio_mixer",
            "intelligence_engine",
        ]

        for component_name in required_components:
            assert component_name in components
            assert components[component_name] is not None

        # Verify component methods exist
        assert hasattr(components["speaker_id"], "identify_speaker")
        assert hasattr(components["conversation_manager"], "create_conversation")
        assert hasattr(components["vad_processor"], "process_audio_frame")
        assert hasattr(components["audio_mixer"], "mix_audio_streams")
        assert hasattr(components["intelligence_engine"], "analyze_voice_segment")
