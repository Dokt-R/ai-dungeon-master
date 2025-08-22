"""
Unit tests for Conversation Intelligence Engine.

Tests cover sentiment analysis, engagement tracking, conversation flow detection,
highlight generation, and real-time conversation analysis capabilities.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from packages.backend.components.conversation_intelligence import (
    ConversationContext,
    ConversationFlow,
    ConversationHighlight,
    ConversationIntelligenceEngine,
    EngagementMetrics,
    SentimentAnalysis,
)


class TestConversationIntelligenceEngine:
    """Test Conversation Intelligence Engine functionality."""

    @pytest.fixture
    def intelligence_engine(self):
        """Create conversation intelligence engine instance."""
        with patch("packages.backend.components.conversation_intelligence.AudioUtils"):
            return ConversationIntelligenceEngine(analysis_window_seconds=300)

    @pytest.fixture
    def sample_segment_data(self):
        """Generate sample segment data for testing."""
        return {
            "segment_id": "segment_1",
            "speaker_id": "user_123",
            "audio_data": np.random.normal(0, 0.5, 1600).astype(
                np.float32
            ),  # 100ms at 16kHz
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow(),
        }

    def test_initialization(self, intelligence_engine):
        """Test engine initialization."""
        assert intelligence_engine.analysis_window == timedelta(seconds=300)
        assert intelligence_engine.conversation_contexts == {}
        assert intelligence_engine.sentiment_threshold_high == 0.3
        assert intelligence_engine.engagement_threshold == 0.7

    @pytest.mark.asyncio
    async def test_analyze_voice_segment_basic(
        self, intelligence_engine, sample_segment_data
    ):
        """Test basic voice segment analysis."""
        conversation_id = "test_conversation_1"

        # Mock internal analysis methods
        intelligence_engine._analyze_sentiment = AsyncMock(
            return_value=SentimentAnalysis(
                segment_id=sample_segment_data["segment_id"],
                speaker_id=sample_segment_data["speaker_id"],
                sentiment_score=0.5,
                confidence=0.8,
                emotion_labels=["positive"],
                intensity=0.6,
            )
        )

        intelligence_engine._analyze_engagement = AsyncMock(
            return_value=EngagementMetrics(
                conversation_id=conversation_id, group_engagement_score=0.7
            )
        )

        intelligence_engine._analyze_conversation_flow = AsyncMock(
            return_value=ConversationFlow(
                conversation_id=conversation_id, rhythm_score=0.8
            )
        )

        intelligence_engine._update_conversation_context = AsyncMock()
        intelligence_engine._detect_highlights = AsyncMock(return_value=[])

        result = await intelligence_engine.analyze_voice_segment(
            conversation_id, sample_segment_data
        )

        assert result["conversation_id"] == conversation_id
        assert "sentiment_analysis" in result
        assert "engagement_metrics" in result
        assert "flow_analysis" in result
        assert "highlights" in result

    @pytest.mark.asyncio
    async def test_analyze_sentiment(self, intelligence_engine, sample_segment_data):
        """Test sentiment analysis functionality."""
        # Mock audio feature extraction
        intelligence_engine._extract_sentiment_features = AsyncMock(
            return_value={
                "pitch": 220.0,
                "rms_energy": 0.3,
                "spectral_centroid": 3500.0,
                "zero_crossing_rate": 0.1,
                "jitter": 0.01,
                "shimmer": 0.03,
            }
        )

        sentiment = await intelligence_engine._analyze_sentiment(sample_segment_data)

        assert isinstance(sentiment, SentimentAnalysis)
        assert sentiment.segment_id == sample_segment_data["segment_id"]
        assert sentiment.speaker_id == sample_segment_data["speaker_id"]
        assert -1.0 <= sentiment.sentiment_score <= 1.0
        assert 0.0 <= sentiment.confidence <= 1.0
        assert isinstance(sentiment.emotion_labels, list)
        assert 0.0 <= sentiment.intensity <= 1.0

    @pytest.mark.asyncio
    async def test_extract_sentiment_features(self, intelligence_engine):
        """Test sentiment feature extraction."""
        audio_data = np.random.normal(0, 0.3, 1600)

        # Mock audio utils methods
        intelligence_engine.audio_utils.calculate_pitch = AsyncMock(return_value=200.0)
        intelligence_engine.audio_utils.calculate_rms_energy = AsyncMock(
            return_value=0.2
        )
        intelligence_engine.audio_utils.calculate_zero_crossing_rate = AsyncMock(
            return_value=0.12
        )

        intelligence_engine._calculate_spectral_centroid = AsyncMock(
            return_value=2800.0
        )
        intelligence_engine._calculate_jitter = AsyncMock(return_value=0.015)
        intelligence_engine._calculate_shimmer = AsyncMock(return_value=0.04)

        features = await intelligence_engine._extract_sentiment_features(audio_data)

        expected_keys = [
            "pitch",
            "rms_energy",
            "spectral_centroid",
            "zero_crossing_rate",
            "jitter",
            "shimmer",
        ]
        assert all(key in features for key in expected_keys)
        assert features["pitch"] == 200.0
        assert features["rms_energy"] == 0.2

    @pytest.mark.asyncio
    async def test_calculate_sentiment_score(self, intelligence_engine):
        """Test sentiment score calculation."""
        features = {
            "pitch": 250.0,  # High pitch
            "rms_energy": 0.2,  # Medium energy
            "spectral_centroid": 3200.0,  # Bright sound
            "zero_crossing_rate": 0.08,  # Low ZCR
        }

        score = await intelligence_engine._calculate_sentiment_score(features)

        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_sentiment_confidence(self, intelligence_engine):
        """Test sentiment confidence calculation."""
        features = {"pitch": 200.0, "rms_energy": 0.3, "spectral_centroid": 3000.0}

        confidence = await intelligence_engine._calculate_sentiment_confidence(features)

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_emotions(self, intelligence_engine):
        """Test emotion detection."""
        features = {
            "pitch": 260.0,  # High pitch -> excited
            "rms_energy": 0.2,  # Medium energy
            "jitter": 0.025,  # High jitter -> nervous
            "shimmer": 0.03,  # Medium shimmer
        }

        emotions = await intelligence_engine._detect_emotions(features)

        assert isinstance(emotions, list)
        assert len(emotions) > 0

    @pytest.mark.asyncio
    async def test_analyze_engagement(self, intelligence_engine, sample_segment_data):
        """Test engagement analysis."""
        conversation_id = "test_conversation_2"

        # Set up conversation context
        context = ConversationContext(conversation_id)
        context.active_speakers = {"user_123": 5, "user_456": 3}
        context.recent_segments = [sample_segment_data]
        intelligence_engine.conversation_contexts[conversation_id] = context

        engagement = await intelligence_engine._analyze_engagement(
            conversation_id, sample_segment_data
        )

        assert isinstance(engagement, EngagementMetrics)
        assert engagement.conversation_id == conversation_id
        assert 0.0 <= engagement.group_engagement_score <= 1.0
        assert 0.0 <= engagement.participation_balance <= 1.0
        assert isinstance(engagement.dominant_speakers, list)
        assert isinstance(engagement.quiet_speakers, list)

    @pytest.mark.asyncio
    async def test_analyze_conversation_flow(
        self, intelligence_engine, sample_segment_data
    ):
        """Test conversation flow analysis."""
        conversation_id = "test_conversation_3"

        # Set up conversation context with some history
        context = ConversationContext(conversation_id)
        context.active_speakers = {"user_123": 5}
        context.last_turn_time = {"user_123": datetime.utcnow() - timedelta(seconds=30)}
        context.pause_events = [{"duration": 1.5}, {"duration": 2.0}, {"duration": 1.8}]
        intelligence_engine.conversation_contexts[conversation_id] = context

        flow = await intelligence_engine._analyze_conversation_flow(
            conversation_id, sample_segment_data
        )

        assert isinstance(flow, ConversationFlow)
        assert flow.conversation_id == conversation_id
        assert 0.0 <= flow.rhythm_score <= 1.0
        assert 0.0 <= flow.flow_smoothness <= 1.0
        assert isinstance(flow.speaking_duration, dict)
        assert isinstance(flow.pause_duration, dict)

    @pytest.mark.asyncio
    async def test_detect_highlights(self, intelligence_engine, sample_segment_data):
        """Test highlight detection."""
        conversation_id = "test_conversation_4"

        sentiment = SentimentAnalysis(
            segment_id=sample_segment_data["segment_id"],
            speaker_id=sample_segment_data["speaker_id"],
            sentiment_score=0.8,  # High positive sentiment
            confidence=0.9,
            emotion_labels=["excited"],
            intensity=0.8,
        )

        engagement = EngagementMetrics(
            conversation_id=conversation_id,
            group_engagement_score=0.9,  # High engagement
        )

        analysis_results = {"sentiment": sentiment, "engagement": engagement}

        highlights = await intelligence_engine._detect_highlights(
            conversation_id, sample_segment_data, analysis_results
        )

        # Should detect highlights for high sentiment and engagement
        assert isinstance(highlights, list)

    @pytest.mark.asyncio
    async def test_create_highlight(self, intelligence_engine, sample_segment_data):
        """Test highlight creation."""
        conversation_id = "test_conversation_5"

        sentiment = SentimentAnalysis(
            segment_id=sample_segment_data["segment_id"],
            speaker_id=sample_segment_data["speaker_id"],
            sentiment_score=0.6,
            confidence=0.8,
            emotion_labels=["positive"],
            intensity=0.7,
        )

        engagement = EngagementMetrics(
            conversation_id=conversation_id, group_engagement_score=0.8
        )

        highlight = await intelligence_engine._create_highlight(
            conversation_id,
            sample_segment_data,
            "emotional_moment",
            sentiment,
            engagement,
        )

        assert isinstance(highlight, ConversationHighlight)
        assert highlight.conversation_id == conversation_id
        assert highlight.highlight_type == "emotional_moment"
        assert highlight.speakers_involved == [sample_segment_data["speaker_id"]]
        assert 0.0 <= highlight.significance_score <= 1.0

    @pytest.mark.asyncio
    async def test_generate_conversation_summary(self, intelligence_engine):
        """Test conversation summary generation."""
        conversation_id = "test_conversation_6"

        # Set up conversation context with data
        context = ConversationContext(conversation_id)
        context.start_time = datetime.utcnow() - timedelta(minutes=30)
        context.active_speakers = {"user_123": 10, "user_456": 8}
        context.recent_segments = [
            {
                "speaker_id": "user_123",
                "timestamp": datetime.utcnow(),
                "analysis": {
                    "sentiment": SentimentAnalysis(
                        segment_id="seg1",
                        speaker_id="user_123",
                        sentiment_score=0.7,
                        confidence=0.8,
                        emotion_labels=["positive"],
                        intensity=0.6,
                    )
                },
            }
        ]
        context.sentiment_history = {"user_123": [0.7, 0.6, 0.8]}
        context.engagement_history = [0.8, 0.7, 0.9]
        intelligence_engine.conversation_contexts[conversation_id] = context

        summary = await intelligence_engine.generate_conversation_summary(
            conversation_id
        )

        assert isinstance(summary, dict)
        assert summary["conversation_id"] == conversation_id
        assert "duration_minutes" in summary
        assert "total_segments" in summary
        assert "active_speakers" in summary
        assert "average_engagement" in summary
        assert "speaker_sentiment" in summary

    @pytest.mark.asyncio
    async def test_cleanup_conversation(self, intelligence_engine):
        """Test conversation cleanup."""
        conversation_id = "test_conversation_7"

        # Set up conversation context
        intelligence_engine.conversation_contexts[conversation_id] = (
            ConversationContext(conversation_id)
        )

        # Verify it exists
        assert conversation_id in intelligence_engine.conversation_contexts

        # Cleanup
        await intelligence_engine.cleanup_conversation(conversation_id)

        # Verify it's removed
        assert conversation_id not in intelligence_engine.conversation_contexts

    @pytest.mark.asyncio
    async def test_get_conversation_stats(self, intelligence_engine):
        """Test conversation statistics retrieval."""
        conversation_id = "test_conversation_8"

        # Test non-existent conversation
        stats = await intelligence_engine.get_conversation_stats(conversation_id)
        assert stats == {}

        # Set up conversation context
        context = ConversationContext(conversation_id)
        context.start_time = datetime.utcnow() - timedelta(minutes=15)
        context.active_speakers = {"user_123": 5, "user_456": 3}
        context.recent_segments = [{}] * 12
        context.sentiment_history = {"user_123": [0.6, 0.7]}
        context.engagement_history = [0.8, 0.7]
        context.interruption_events = [{"speaker_id": "user_123"}] * 2
        context.pause_events = [{"duration": 1.5}] * 3
        intelligence_engine.conversation_contexts[conversation_id] = context

        stats = await intelligence_engine.get_conversation_stats(conversation_id)

        expected_keys = [
            "conversation_id",
            "active_speakers",
            "total_segments",
            "sentiment_history_length",
            "engagement_history_length",
            "interruption_count",
            "pause_count",
            "duration_minutes",
        ]

        for key in expected_keys:
            assert key in stats

        assert stats["conversation_id"] == conversation_id
        assert stats["active_speakers"] == 2
        assert stats["total_segments"] == 12

    def test_calculate_spectral_centroid(self, intelligence_engine):
        """Test spectral centroid calculation."""
        audio_data = np.random.normal(0, 0.5, 1600)

        centroid = asyncio.run(
            intelligence_engine._calculate_spectral_centroid(audio_data)
        )

        assert isinstance(centroid, float)
        assert centroid >= 0.0

    def test_calculate_jitter(self, intelligence_engine):
        """Test jitter calculation."""
        audio_data = np.random.normal(0, 0.5, 1600)

        jitter = asyncio.run(intelligence_engine._calculate_jitter(audio_data))

        assert isinstance(jitter, float)
        assert 0.0 <= jitter <= 1.0

    def test_calculate_shimmer(self, intelligence_engine):
        """Test shimmer calculation."""
        audio_data = np.random.normal(0, 0.5, 1600)

        shimmer = asyncio.run(intelligence_engine._calculate_shimmer(audio_data))

        assert isinstance(shimmer, float)
        assert 0.0 <= shimmer <= 1.0

    @pytest.mark.asyncio
    async def test_update_conversation_context(
        self, intelligence_engine, sample_segment_data
    ):
        """Test conversation context updates."""
        conversation_id = "test_conversation_9"

        # Initialize context
        context = ConversationContext(conversation_id)
        intelligence_engine.conversation_contexts[conversation_id] = context

        analysis_results = {
            "sentiment": SentimentAnalysis(
                segment_id=sample_segment_data["segment_id"],
                speaker_id=sample_segment_data["speaker_id"],
                sentiment_score=0.5,
                confidence=0.8,
                emotion_labels=["neutral"],
                intensity=0.5,
            ),
            "engagement": EngagementMetrics(
                conversation_id=conversation_id, group_engagement_score=0.7
            ),
        }

        await intelligence_engine._update_conversation_context(
            conversation_id, sample_segment_data, analysis_results
        )

        updated_context = intelligence_engine.conversation_contexts[conversation_id]

        assert sample_segment_data["speaker_id"] in updated_context.active_speakers
        assert len(updated_context.recent_segments) == 1
        assert sample_segment_data["speaker_id"] in updated_context.sentiment_history
        assert len(updated_context.engagement_history) == 1


class TestSentimentAnalysis:
    """Test SentimentAnalysis model."""

    def test_sentiment_analysis_defaults(self):
        """Test sentiment analysis default values."""
        analysis = SentimentAnalysis(
            segment_id="seg1",
            speaker_id="user123",
            sentiment_score=0.0,
            confidence=0.0,
            intensity=0.0,
        )

        assert analysis.segment_id == "seg1"
        assert analysis.speaker_id == "user123"
        assert analysis.sentiment_score == 0.0
        assert analysis.confidence == 0.0
        assert analysis.intensity == 0.0
        assert analysis.emotion_labels == []
        assert isinstance(analysis.timestamp, datetime)


class TestEngagementMetrics:
    """Test EngagementMetrics model."""

    def test_engagement_metrics_defaults(self):
        """Test engagement metrics default values."""
        metrics = EngagementMetrics(conversation_id="conv1")

        assert metrics.conversation_id == "conv1"
        assert metrics.speaker_engagement == {}
        assert metrics.group_engagement_score == 0.0
        assert metrics.participation_balance == 0.0
        assert metrics.interaction_frequency == 0.0
        assert metrics.dominant_speakers == []
        assert metrics.quiet_speakers == []
        assert isinstance(metrics.timestamp, datetime)


class TestConversationFlow:
    """Test ConversationFlow model."""

    def test_conversation_flow_defaults(self):
        """Test conversation flow default values."""
        flow = ConversationFlow(conversation_id="conv1")

        assert flow.conversation_id == "conv1"
        assert flow.turn_taking_pattern == []
        assert flow.speaking_duration == {}
        assert flow.pause_duration == {}
        assert flow.interruption_count == {}
        assert flow.rhythm_score == 0.0
        assert flow.flow_smoothness == 0.0
        assert isinstance(flow.timestamp, datetime)


class TestConversationHighlight:
    """Test ConversationHighlight model."""

    def test_conversation_highlight_creation(self):
        """Test conversation highlight creation."""
        highlight = ConversationHighlight(
            highlight_id="highlight1",
            conversation_id="conv1",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            highlight_type="emotional_moment",
            speakers_involved=["user123"],
            sentiment_score=0.8,
            engagement_score=0.9,
            significance_score=0.85,
            description="Emotional moment detected",
        )

        assert highlight.highlight_id == "highlight1"
        assert highlight.conversation_id == "conv1"
        assert highlight.highlight_type == "emotional_moment"
        assert highlight.speakers_involved == ["user123"]
        assert highlight.sentiment_score == 0.8
        assert highlight.engagement_score == 0.9
        assert highlight.significance_score == 0.85


class TestConversationContext:
    """Test ConversationContext management."""

    def test_conversation_context_defaults(self):
        """Test conversation context default values."""
        context = ConversationContext(conversation_id="conv1")

        assert context.conversation_id == "conv1"
        assert context.active_speakers == {}
        assert context.recent_segments == []
        assert context.sentiment_history == {}
        assert context.engagement_history == []
        assert context.last_turn_time == {}
        assert context.interruption_events == []
        assert context.pause_events == []
        assert isinstance(context.start_time, datetime)
