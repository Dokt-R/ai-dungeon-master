# Audio Services Usage Guide

## Overview

The Audio Services provide comprehensive audio processing, mixing, streaming, and speech capabilities for the AI Dungeon Master system. This collection includes multiple specialized services for handling voice interactions, audio enhancement, speech-to-text, and text-to-speech conversion.

### Purpose
- Real-time audio processing and enhancement
- Multi-user voice mixing and spatial audio
- Speech-to-text and text-to-speech conversion
- Audio streaming optimization for Discord
- Voice activity detection and speaker identification
- Audio quality assessment and improvement

## Key Components

### Core Audio Services

#### `AudioProcessingService` (`packages/backend/components/audio_processing_service.py`)
Core audio processing and enhancement service.

**Key Methods:**
- `process_audio_data(audio_data, input_format, correlation_id)` - Process audio data
- `convert_for_stt(audio_data, input_format)` - Convert audio for STT
- `convert_for_tts(audio_data, input_format)` - Convert audio for TTS
- `enhance_audio_quality(audio_data, format)` - Enhance audio quality
- `process_stream_audio(stream_id, audio_data, format)` - Process streaming audio

#### `AudioMixerService` (`packages/backend/components/audio_mixer_service.py`)
Advanced audio mixing with spatial positioning and ducking.

**Key Methods:**
- `create_mix_session(session_id)` - Create audio mixing session
- `add_audio_source(session_id, source)` - Add audio source to session
- `mix_audio_streams(session_id, audio_streams)` - Mix multiple audio streams
- `update_source_position(session_id, source_id, position)` - Update spatial position
- `set_focus_mode(session_id, speaker_id, enable)` - Set focus mode
- `cleanup_session(session_id)` - Clean up mixing session

#### `STTService` (`packages/backend/components/stt_service.py`)
Speech-to-text conversion with multiple provider support.

**Key Methods:**
- `transcribe_audio(request, correlation_id)` - Transcribe audio to text
- `get_health_status()` - Get service health status
- `get_supported_formats()` - Get supported audio formats
- `validate_audio_data(audio_data, format)` - Validate audio data

#### `TTSService` (`packages/backend/components/tts_service.py`)
Text-to-speech conversion with voice selection.

**Key Methods:**
- `generate_speech(request, correlation_id)` - Generate speech from text
- `get_available_voices()` - Get available voice options
- `validate_text(text)` - Validate input text
- `estimate_audio_length(text, voice)` - Estimate audio duration

#### `AdvancedVADProcessor` (`packages/backend/components/advanced_vad_processor.py`)
Voice activity detection with noise filtering and speaker identification.

**Key Methods:**
- `process_audio_frame(session_id, audio_data, speaker_id)` - Process audio frame
- `get_voice_segments(session_id)` - Get detected voice segments
- `update_noise_profile(session_id, audio_data)` - Update noise profile
- `reset_session(session_id)` - Reset VAD session

#### `AudioStreamOptimizer` (`packages/backend/components/audio_stream_optimizer.py`)
Streaming audio optimization for real-time performance.

**Key Methods:**
- `optimize_stream(stream_id, audio_data, session_context)` - Optimize audio stream
- `process_parallel(audio_data, text_data, session_context)` - Process audio and text in parallel
- `get_stream_metrics(stream_id)` - Get stream performance metrics
- `cleanup_stream(stream_id)` - Clean up stream resources

#### `AudioQualityAssessor` (`packages/backend/components/audio_quality_assessor.py`)
Audio quality assessment and improvement.

**Key Methods:**
- `assess_quality(audio_data, format)` - Assess audio quality
- `get_quality_metrics(audio_data, format)` - Get detailed quality metrics
- `suggest_improvements(quality_metrics)` - Suggest quality improvements
- `apply_recommendations(audio_data, format, recommendations)` - Apply quality improvements

#### `AudioUtils` (`packages/backend/components/audio_utils.py`)
Utility functions for audio processing.

**Key Methods:**
- `calculate_rms_energy(audio_data)` - Calculate RMS energy
- `calculate_zero_crossing_rate(audio_data)` - Calculate zero crossing rate
- `calculate_spectral_centroid(audio_data)` - Calculate spectral centroid
- `detect_silence(audio_data, threshold)` - Detect silence periods
- `normalize_audio(audio_data, target_level)` - Normalize audio level

## Dependencies

### Internal Dependencies
- `numpy` - Audio signal processing
- `packages.shared.logging_config` - Structured logging
- `packages.shared.correlation` - Correlation ID management
- `packages.backend.components.observability_service` - Tracing integration

### External Dependencies
- Audio processing libraries (depending on implementation)
- Voice activity detection libraries
- Speech recognition providers (OpenAI, Google, etc.)
- Text-to-speech providers (OpenAI, ElevenLabs, etc.)

## Configuration

### Audio Processing Configuration

```python
# Audio processing settings
audio_config = {
    "sample_rate": 16000,
    "channels": 1,
    "bit_depth": 16,
    "buffer_size": 1024,
    "overlap": 512
}

# Enhancement settings
enhancement_config = {
    "noise_reduction": True,
    "echo_cancellation": True,
    "volume_normalization": True,
    "silence_threshold": 0.01,
    "min_duration": 0.5
}
```

### Environment Variables

```bash
# STT Configuration
export STT_PROVIDER="openai"
export STT_API_KEY="your_stt_api_key"
export STT_MODEL="whisper-1"
export STT_LANGUAGE="en"

# TTS Configuration
export TTS_PROVIDER="openai"
export TTS_API_KEY="your_tts_api_key"
export TTS_MODEL="tts-1"
export TTS_VOICE="alloy"

# Audio Processing
export AUDIO_SAMPLE_RATE="16000"
export AUDIO_CHANNELS="1"
export AUDIO_BUFFER_SIZE="1024"
export AUDIO_ENABLE_ENHANCEMENT="true"
export AUDIO_NOISE_REDUCTION="true"
```

## Usage Examples

### Basic Audio Processing

```python
from packages.backend.components.audio_processing_service import audio_processing_service

# Process audio data
async def process_audio(audio_data: bytes, input_format: str, correlation_id: str):
    """Process audio with enhancement."""

    result = await audio_processing_service.process_audio_data(
        audio_data=audio_data,
        input_format=input_format,
        correlation_id=correlation_id
    )

    if result.success:
        print(f"Processed audio: {len(result.processed_data)} bytes")
        print(f"Quality score: {result.quality_score}")
        return result.processed_data
    else:
        print(f"Processing failed: {result.error}")
        return None
```

### Speech-to-Text Conversion

```python
from packages.backend.components.stt_service import stt_service
from packages.shared.models import AudioTranscriptionRequest

# Transcribe audio
async def transcribe_audio(audio_data: bytes, audio_format: str, language: str = "en"):
    """Convert speech to text."""

    request = AudioTranscriptionRequest(
        audio_data=audio_data,
        audio_format=audio_format,
        language=language
    )

    result = await stt_service.transcribe_audio(request, "correlation_123")

    if result.success:
        print(f"Transcription: {result.transcription}")
        print(f"Confidence: {result.confidence}")
        print(f"Language: {result.detected_language}")
        return result.transcription
    else:
        print(f"Transcription failed: {result.error}")
        return None
```

### Text-to-Speech Conversion

```python
from packages.backend.components.tts_service import tts_service
from packages.shared.models import SpeechSynthesisRequest

# Generate speech
async def generate_speech(text: str, voice: str = "alloy"):
    """Convert text to speech."""

    request = SpeechSynthesisRequest(
        text=text,
        voice=voice,
        speed=1.0
    )

    result = await tts_service.generate_speech(request, "correlation_123")

    if result.success:
        print(f"Generated audio: {len(result.audio_data)} bytes")
        print(f"Duration: {result.duration}s")
        print(f"Format: {result.audio_format}")
        return result.audio_data
    else:
        print(f"Speech generation failed: {result.error}")
        return None
```

### Audio Mixing and Spatial Audio

```python
from packages.backend.components.audio_mixer_service import audio_mixer_service
from packages.shared.models import AudioSource, SpatialPosition

# Create audio mixing session
async def create_audio_mix_session(session_id: str):
    """Create audio mixing session with multiple sources."""

    # Create session
    success = await audio_mixer_service.create_mix_session(session_id)
    if not success:
        print("Failed to create mixing session")
        return

    # Add audio sources with spatial positioning
    sources = [
        {
            "source_id": "user_123",
            "user_id": "user_123",
            "position": SpatialPosition(x=0.0, y=0.0, z=0.0, distance=1.0)
        },
        {
            "source_id": "user_456",
            "user_id": "user_456",
            "position": SpatialPosition(x=1.0, y=0.0, z=0.0, distance=2.0)
        },
        {
            "source_id": "dm_789",
            "user_id": "dm_789",
            "position": SpatialPosition(x=0.0, y=0.0, z=0.0, distance=1.0)
        }
    ]

    for source_config in sources:
        source = AudioSource(**source_config)
        await audio_mixer_service.add_audio_source(session_id, source)
```

### Voice Activity Detection

```python
from packages.backend.components.advanced_vad_processor import AdvancedVADProcessor

# Process audio with VAD
async def process_voice_audio(session_id: str, audio_data: bytes, speaker_id: str):
    """Process audio with voice activity detection."""

    vad_processor = AdvancedVADProcessor()

    segments = await vad_processor.process_audio_frame(
        session_id=session_id,
        audio_data=audio_data,
        speaker_id=speaker_id
    )

    for segment in segments:
        if segment.is_speech:
            print(f"Voice detected: {segment.speaker_id}")
            print(f"Start time: {segment.start_time}")
            print(f"End time: {segment.end_time}")
            print(f"Energy level: {segment.energy_level}")
        else:
            print("Non-speech audio detected")
```

### Audio Streaming Optimization

```python
from packages.backend.components.audio_stream_optimizer import audio_stream_optimizer

# Optimize streaming audio
async def optimize_audio_stream(stream_id: str, audio_data: bytes):
    """Optimize audio stream for real-time processing."""

    optimized_audio, metadata = await audio_stream_optimizer.optimize_stream(
        stream_id=stream_id,
        audio_data=audio_data,
        session_context={"user_id": "user_123", "priority": "high"}
    )

    print(f"Original size: {metadata.get('original_size')} bytes")
    print(f"Optimized size: {metadata.get('optimized_size')} bytes")
    print(f"Quality improvement: {metadata.get('quality_improvement')}")

    return optimized_audio
```

### Complete Voice Pipeline

```python
# Complete voice interaction pipeline
async def process_voice_interaction(audio_data: bytes, user_id: str, session_id: str):
    """Complete voice processing pipeline."""

    # 1. Process audio with VAD
    vad_segments = await AdvancedVADProcessor.process_audio_frame(
        session_id=session_id,
        audio_data=audio_data,
        speaker_id=user_id
    )

    # 2. Extract speech segments
    speech_segments = [s for s in vad_segments if s.is_speech]

    if not speech_segments:
        print("No speech detected")
        return

    # 3. Transcribe speech
    transcription_request = AudioTranscriptionRequest(
        audio_data=audio_data,
        audio_format="wav",
        language="en"
    )

    transcription_result = await stt_service.transcribe_audio(
        transcription_request, session_id
    )

    if not transcription_result.success:
        print(f"Transcription failed: {transcription_result.error}")
        return

    # 4. Process transcription with AI
    ai_response = await ai_client.generate_text(
        prompt=f"Respond to: {transcription_result.transcription}"
    )

    # 5. Generate speech response
    tts_request = SpeechSynthesisRequest(
        text=ai_response,
        voice="alloy"
    )

    speech_result = await tts_service.generate_speech(tts_request, session_id)

    if speech_result.success:
        # 6. Add to audio mix
        await audio_mixer_service.add_audio_source(
            session_id,
            AudioSource(
                source_id=f"ai_response_{user_id}",
                user_id="ai_dm",
                position=SpatialPosition(x=0.0, y=0.0, z=0.0, distance=1.0)
            )
        )

        print("Voice interaction completed successfully")
        return speech_result.audio_data
    else:
        print(f"Speech generation failed: {speech_result.error}")
        return None
```

## Integration Points

### With Discord Bot

```python
# packages/bot/services/voice_manager.py
from packages.backend.components.audio_mixer_service import audio_mixer_service
from packages.backend.components.stt_service import stt_service
from packages.backend.components.tts_service import tts_service

class VoiceManager:
    """Discord voice channel manager with audio services integration."""

    def __init__(self, bot):
        self.bot = bot
        self.audio_mixer = audio_mixer_service
        self.stt_service = stt_service
        self.tts_service = tts_service

    async def handle_voice_data(self, user_id: str, audio_data: bytes, session_id: str):
        """Handle voice data from Discord."""

        # Add user to audio mix
        source = AudioSource(
            source_id=str(user_id),
            user_id=str(user_id),
            position=SpatialPosition(x=0.0, y=0.0, z=0.0, distance=1.0)
        )

        await self.audio_mixer.add_audio_source(session_id, source)

        # Transcribe speech
        transcription_request = AudioTranscriptionRequest(
            audio_data=audio_data,
            audio_format="wav",
            language="en"
        )

        transcription = await self.stt_service.transcribe_audio(
            transcription_request, session_id
        )

        if transcription.success:
            # Process with AI and generate response
            ai_response = await self.generate_ai_response(transcription.transcription)

            # Convert to speech
            speech_request = SpeechSynthesisRequest(
                text=ai_response,
                voice="alloy"
            )

            speech_result = await self.tts_service.generate_speech(
                speech_request, session_id
            )

            if speech_result.success:
                # Play audio in Discord voice channel
                await self.play_audio(speech_result.audio_data, session_id)
```

### With Conversation Intelligence

```python
# packages/backend/components/conversation_intelligence.py
from packages.backend.components.advanced_vad_processor import AdvancedVADProcessor
from packages.backend.components.audio_mixer_service import audio_mixer_service

class ConversationIntelligenceEngine:
    """Conversation intelligence with audio processing."""

    def __init__(self):
        self.vad_processor = AdvancedVADProcessor()
        self.audio_mixer = audio_mixer_service

    async def analyze_voice_segment(self, session_id: str, audio_data: bytes, speaker_id: str):
        """Analyze voice segment for conversation intelligence."""

        # Process with VAD
        segments = await self.vad_processor.process_audio_frame(
            session_id=session_id,
            audio_data=audio_data,
            speaker_id=speaker_id
        )

        # Extract voice features
        voice_features = []
        for segment in segments:
            if segment.is_speech:
                features = await self._extract_voice_features(segment)
                voice_features.append(features)

        # Analyze conversation patterns
        conversation_analysis = await self._analyze_conversation_patterns(
            voice_features, session_id
        )

        # Adjust audio mixing based on analysis
        if conversation_analysis["speaker_dominance"]:
            dominant_speaker = conversation_analysis["dominant_speaker"]
            await self.audio_mixer.set_focus_mode(
                session_id, dominant_speaker, enable=True
            )

        return conversation_analysis
```

### With Memory Service

```python
# packages/backend/components/memory_service.py
from packages.backend.components.stt_service import stt_service
from packages.backend.components.audio_quality_assessor import audio_quality_assessor

class MemoryService:
    """Memory service with audio transcription and quality assessment."""

    async def store_voice_memory(self, audio_data: bytes, metadata: dict):
        """Store voice data with transcription and quality assessment."""

        # Assess audio quality
        quality_metrics = await audio_quality_assessor.assess_quality(
            audio_data, "wav"
        )

        # Transcribe audio
        transcription_request = AudioTranscriptionRequest(
            audio_data=audio_data,
            audio_format="wav"
        )

        transcription = await stt_service.transcribe_audio(
            transcription_request, metadata.get("correlation_id", "unknown")
        )

        # Store memory with audio metadata
        memory_entry = {
            "type": "voice_memory",
            "audio_data": audio_data,
            "transcription": transcription.transcription if transcription.success else None,
            "quality_metrics": quality_metrics,
            "metadata": metadata,
            "timestamp": datetime.utcnow()
        }

        await self._store_memory(memory_entry)
```

## Error Handling

### Audio Processing Failures

```python
# Handle audio processing errors gracefully
async def safe_audio_processing(audio_data: bytes, operation: str):
    """Process audio with comprehensive error handling."""

    try:
        # Validate input
        if not audio_data or len(audio_data) == 0:
            raise AudioProcessingError("Empty audio data")

        # Process audio
        if operation == "enhance":
            result = await audio_processing_service.enhance_audio_quality(
                audio_data, "wav"
            )
        elif operation == "convert_stt":
            converted, format = await audio_processing_service.convert_for_stt(
                audio_data, "wav"
            )
            result = {"data": converted, "format": format}
        elif operation == "convert_tts":
            converted, format = await audio_processing_service.convert_for_tts(
                audio_data, "wav"
            )
            result = {"data": converted, "format": format}
        else:
            raise AudioProcessingError(f"Unknown operation: {operation}")

        if not result.get("success", True):
            raise AudioProcessingError(result.get("error", "Processing failed"))

        return result

    except AudioProcessingError as e:
        logger.error(f"Audio processing failed: {e}")
        # Return original data if processing fails
        return {"data": audio_data, "format": "wav", "processed": False}

    except Exception as e:
        logger.error(f"Unexpected audio processing error: {e}")
        # Return minimal result on unexpected errors
        return {"data": audio_data, "format": "wav", "error": str(e)}
```

### STT/TTS Service Failures

```python
# Handle speech service failures with fallbacks
async def safe_speech_conversion(text_or_audio, operation: str, correlation_id: str):
    """Convert speech with fallback handling."""

    try:
        if operation == "text_to_speech":
            request = SpeechSynthesisRequest(text=text_or_audio, voice="alloy")
            result = await tts_service.generate_speech(request, correlation_id)

            if result.success:
                return result.audio_data
            else:
                logger.warning(f"TTS failed: {result.error}")
                # Return empty audio as fallback
                return b""

        elif operation == "speech_to_text":
            request = AudioTranscriptionRequest(
                audio_data=text_or_audio, audio_format="wav"
            )
            result = await stt_service.transcribe_audio(request, correlation_id)

            if result.success:
                return result.transcription
            else:
                logger.warning(f"STT failed: {result.error}")
                # Return empty transcription as fallback
                return ""

        else:
            raise ValueError(f"Unknown operation: {operation}")

    except Exception as e:
        logger.error(f"Speech conversion failed: {e}")
        # Return appropriate fallback
        return "" if operation == "speech_to_text" else b""
```

### Audio Mixing Failures

```python
# Handle audio mixing failures
async def safe_audio_mixing(session_id: str, audio_streams: dict):
    """Mix audio streams with error handling."""

    try:
        # Validate session
        session_state = await audio_mixer_service.get_mixing_state(session_id)
        if not session_state:
            logger.warning(f"Mixing session {session_id} not found")
            # Create session if it doesn't exist
            await audio_mixer_service.create_mix_session(session_id)

        # Validate audio streams
        valid_streams = {}
        for source_id, audio_data in audio_streams.items():
            if audio_data is not None and len(audio_data) > 0:
                valid_streams[source_id] = audio_data
            else:
                logger.warning(f"Invalid audio data for source {source_id}")

        if not valid_streams:
            logger.warning("No valid audio streams to mix")
            # Return silent audio
            return np.zeros((1024, 2), dtype=np.float32)

        # Mix streams
        mixed_audio = await audio_mixer_service.mix_audio_streams(
            session_id, valid_streams
        )

        return mixed_audio

    except Exception as e:
        logger.error(f"Audio mixing failed: {e}")
        # Return silent audio as fallback
        return np.zeros((1024, 2), dtype=np.float32)
```

## Performance Considerations

### Audio Processing Optimization

```python
# Optimize audio processing for performance
class AudioProcessingOptimizer:
    """Optimize audio processing operations."""

    def __init__(self):
        self.processing_cache = {}
        self.max_cache_size = 100

    async def process_with_caching(self, audio_data: bytes, operation: str):
        """Process audio with intelligent caching."""

        # Generate cache key
        import hashlib
        cache_key = hashlib.md5(audio_data[:1024]).hexdigest() + f"_{operation}"

        # Check cache
        if cache_key in self.processing_cache:
            return self.processing_cache[cache_key]

        # Process audio
        result = await self._process_audio(audio_data, operation)

        # Cache result
        if len(self.processing_cache) < self.max_cache_size:
            self.processing_cache[cache_key] = result

        return result

    async def _process_audio(self, audio_data: bytes, operation: str):
        """Internal audio processing."""
        if operation == "enhance":
            return await audio_processing_service.enhance_audio_quality(audio_data, "wav")
        elif operation == "convert":
            return await audio_processing_service.convert_for_stt(audio_data, "wav")
        else:
            return audio_data
```

### Memory Management

```python
# Manage audio data memory usage
class AudioMemoryManager:
    """Manage memory usage for audio data."""

    def __init__(self, max_memory_mb: int = 100):
        self.max_memory_mb = max_memory_mb
        self.current_memory_mb = 0
        self.audio_cache = {}

    def can_allocate(self, size_bytes: int) -> bool:
        """Check if memory can be allocated."""
        size_mb = size_bytes / (1024 * 1024)
        return (self.current_memory_mb + size_mb) <= self.max_memory_mb

    def allocate_audio(self, audio_id: str, audio_data: bytes):
        """Allocate audio data in memory."""
        size_mb = len(audio_data) / (1024 * 1024)

        if not self.can_allocate(len(audio_data)):
            self._evict_oldest()

        self.audio_cache[audio_id] = audio_data
        self.current_memory_mb += size_mb

    def _evict_oldest(self):
        """Evict oldest audio data to free memory."""
        if not self.audio_cache:
            return

        # Remove oldest entry (simple FIFO)
        oldest_id = next(iter(self.audio_cache))
        size_mb = len(self.audio_cache[oldest_id]) / (1024 * 1024)

        del self.audio_cache[oldest_id]
        self.current_memory_mb -= size_mb

    def get_audio(self, audio_id: str) -> bytes:
        """Get audio data from memory."""
        return self.audio_cache.get(audio_id)
```

### Streaming Optimization

```python
# Optimize real-time audio streaming
class StreamingAudioOptimizer:
    """Optimize audio streaming for real-time performance."""

    def __init__(self):
        self.stream_buffers = {}
        self.processing_queue = asyncio.Queue()

    async def optimize_stream(self, stream_id: str, audio_chunk: bytes):
        """Optimize audio chunk for streaming."""

        # Add to stream buffer
        if stream_id not in self.stream_buffers:
            self.stream_buffers[stream_id] = []

        self.stream_buffers[stream_id].append(audio_chunk)

        # Process in background if enough data
        if len(self.stream_buffers[stream_id]) >= 5:  # Process every 5 chunks
            chunks = self.stream_buffers[stream_id].copy()
            self.stream_buffers[stream_id].clear()

            # Queue for background processing
            await self.processing_queue.put((stream_id, chunks))

            # Start background processing if not already running
            if not hasattr(self, '_processing_task'):
                self._processing_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Process audio chunks in background."""
        while True:
            try:
                stream_id, chunks = await self.processing_queue.get()

                # Combine chunks
                combined_audio = b"".join(chunks)

                # Process combined audio
                optimized_audio, metadata = await audio_stream_optimizer.optimize_stream(
                    stream_id, combined_audio
                )

                # Handle optimized audio (send to mixer, etc.)
                await self._handle_optimized_audio(stream_id, optimized_audio, metadata)

                self.processing_queue.task_done()

            except Exception as e:
                logger.error(f"Stream processing error: {e}")
```

## Best Practices

### 1. Audio Format Management

```python
# Standardize audio format handling
AUDIO_FORMAT_CONFIG = {
    "stt": {
        "sample_rate": 16000,
        "channels": 1,
        "bit_depth": 16,
        "format": "wav"
    },
    "tts": {
        "sample_rate": 22050,
        "channels": 1,
        "bit_depth": 16,
        "format": "wav"
    },
    "mixing": {
        "sample_rate": 48000,
        "channels": 2,
        "bit_depth": 32,
        "format": "float32"
    }
}

async def standardize_audio_format(audio_data: bytes, target_format: str):
    """Standardize audio to target format."""
    config = AUDIO_FORMAT_CONFIG[target_format]

    # Convert audio format
    converted_data, output_format = await audio_processing_service.convert_for_stt(
        audio_data, "wav"
    )

    # Validate format
    if output_format != config["format"]:
        logger.warning(f"Audio format mismatch: expected {config['format']}, got {output_format}")

    return converted_data
```

### 2. Quality Assessment and Improvement

```python
# Implement comprehensive audio quality management
async def process_audio_with_quality_assurance(audio_data: bytes, audio_format: str):
    """Process audio with quality assurance."""

    # Assess initial quality
    quality_metrics = await audio_quality_assessor.assess_quality(
        audio_data, audio_format
    )

    print(f"Initial quality score: {quality_metrics.overall_score}")

    # Check if improvement is needed
    if quality_metrics.overall_score < 0.7:
        print("Audio quality needs improvement")

        # Get improvement suggestions
        suggestions = audio_quality_assessor.suggest_improvements(quality_metrics)

        # Apply improvements
        improved_audio = await audio_quality_assessor.apply_recommendations(
            audio_data, audio_format, suggestions
        )

        # Re-assess quality
        improved_metrics = await audio_quality_assessor.assess_quality(
            improved_audio, audio_format
        )

        print(f"Improved quality score: {improved_metrics.overall_score}")

        return improved_audio
    else:
        print("Audio quality is acceptable")
        return audio_data
```

### 3. Resource Management

```python
# Implement proper resource management
class AudioResourceManager:
    """Manage audio processing resources."""

    def __init__(self):
        self.active_sessions = set()
        self.session_resources = {}

    async def create_audio_session(self, session_id: str):
        """Create audio session with resource allocation."""
        if session_id in self.active_sessions:
            raise ValueError(f"Session {session_id} already exists")

        # Initialize session resources
        session_resources = {
            "vad_processor": await self._init_vad_processor(session_id),
            "audio_mixer": await self._init_audio_mixer(session_id),
            "stream_optimizer": await self._init_stream_optimizer(session_id)
        }

        self.session_resources[session_id] = session_resources
        self.active_sessions.add(session_id)

        return session_resources

    async def cleanup_session(self, session_id: str):
        """Clean up session resources."""
        if session_id not in self.active_sessions:
            return

        # Clean up resources
        resources = self.session_resources.get(session_id, {})
        for resource_name, resource in resources.items():
            try:
                if hasattr(resource, 'cleanup'):
                    await resource.cleanup()
                elif hasattr(resource, 'close'):
                    await resource.close()
            except Exception as e:
                logger.error(f"Error cleaning up {resource_name}: {e}")

        # Remove from tracking
        self.active_sessions.discard(session_id)
        self.session_resources.pop(session_id, None)

    async def _init_vad_processor(self, session_id: str):
        """Initialize VAD processor for session."""
        vad = AdvancedVADProcessor()
        await vad.reset_session(session_id)
        return vad

    async def _init_audio_mixer(self, session_id: str):
        """Initialize audio mixer for session."""
        success = await audio_mixer_service.create_mix_session(session_id)
        if not success:
            raise RuntimeError(f"Failed to create audio mix session {session_id}")
        return audio_mixer_service

    async def _init_stream_optimizer(self, session_id: str):
        """Initialize stream optimizer for session."""
        return audio_stream_optimizer
```

### 4. Error Recovery and Resilience

```python
# Implement error recovery mechanisms
async def process_audio_with_recovery(audio_data: bytes, operation: str, max_retries: int = 3):
    """Process audio with automatic error recovery."""

    for attempt in range(max_retries + 1):
        try:
            if operation == "stt":
                request = AudioTranscriptionRequest(audio_data=audio_data, audio_format="wav")
                result = await stt_service.transcribe_audio(request, "recovery_attempt")
            elif operation == "tts":
                request = SpeechSynthesisRequest(text="Test audio")
                result = await tts_service.generate_speech(request, "recovery_attempt")
            elif operation == "mix":
                result = await audio_mixer_service.mix_audio_streams("test_session", {"test": audio_data})
            else:
                result = await audio_processing_service.process_audio_data(
                    audio_data, "wav", "recovery_attempt"
                )

            if result.get("success", True):
                return result
            else:
                raise RuntimeError(result.get("error", "Processing failed"))

        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Audio processing failed after {max_retries + 1} attempts: {e}")
                raise
            else:
                logger.warning(f"Audio processing attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    raise RuntimeError("Audio processing failed after all retries")
```

### 5. Monitoring and Observability

```python
# Implement comprehensive audio monitoring
async def monitor_audio_pipeline(session_id: str, audio_data: bytes):
    """Monitor audio pipeline performance and quality."""

    start_time = time.time()

    # Monitor each processing stage
    stages = [
        ("vad", lambda: AdvancedVADProcessor.process_audio_frame(session_id, audio_data, "monitor")),
        ("stt", lambda: stt_service.transcribe_audio(
            AudioTranscriptionRequest(audio_data=audio_data, audio_format="wav"), session_id
        )),
        ("quality", lambda: audio_quality_assessor.assess_quality(audio_data, "wav"))
    ]

    results = {}
    for stage_name, stage_func in stages:
        stage_start = time.time()
        try:
            result = await stage_func()
            stage_duration = time.time() - stage_start
            results[stage_name] = {
                "success": True,
                "duration": stage_duration,
                "result": result
            }
        except Exception as e:
            stage_duration = time.time() - stage_start
            results[stage_name] = {
                "success": False,
                "duration": stage_duration,
                "error": str(e)
            }

    total_duration = time.time() - start_time

    # Log monitoring results
    logger.info(
        "audio_pipeline_monitoring",
        session_id=session_id,
        total_duration=total_duration,
        stages=results
    )

    # Check for performance issues
    slow_stages = [
        name for name, result in results.items()
        if result["success"] and result["duration"] > 1.0
    ]

    if slow_stages:
        logger.warning(
            "slow_audio_stages",
            session_id=session_id,
            slow_stages=slow_stages,
            total_duration=total_duration
        )

    return results
```

## Troubleshooting

### Common Issues

#### 1. Audio Format Compatibility

```python
# Diagnose audio format issues
async def diagnose_audio_format(audio_data: bytes, expected_format: str):
    """Diagnose audio format compatibility issues."""

    issues = []

    try:
        # Check file header
        if len(audio_data) < 44:
            issues.append("Audio data too small to contain valid header")

        # Check WAV header
        if expected_format == "wav" and len(audio_data) >= 44:
            riff_header = audio_data[0:4]
            if riff_header != b"RIFF":
                issues.append("Invalid WAV header - missing RIFF")

            wave_header = audio_data[8:12]
            if wave_header != b"WAVE":
                issues.append("Invalid WAV header - missing WAVE")

        # Try processing with service
        result = await audio_processing_service.process_audio_data(
            audio_data, expected_format, "diagnosis"
        )

        if not result.success:
            issues.append(f"Processing failed: {result.error}")

    except Exception as e:
        issues.append(f"Format diagnosis error: {e}")

    return issues
```

#### 2. Audio Quality Problems

```python
# Troubleshoot audio quality issues
async def troubleshoot_audio_quality(audio_data: bytes, audio_format: str):
    """Troubleshoot audio quality problems."""

    try:
        # Assess quality
        quality_metrics = await audio_quality_assessor.assess_quality(
            audio_data, audio_format
        )

        issues = []

        # Check individual metrics
        if quality_metrics.noise_level > 0.3:
            issues.append(".2f")

        if quality_metrics.volume_level < 0.1:
            issues.append(".2f")

        if quality_metrics.clipping_detected:
            issues.append("Audio clipping detected")

        if quality_metrics.silence_ratio > 0.8:
            issues.append(".2%")

        # Get improvement suggestions
        if issues:
            suggestions = audio_quality_assessor.suggest_improvements(quality_metrics)
            issues.append(f"Suggestions: {suggestions}")

        return issues

    except Exception as e:
        return [f"Quality assessment failed: {e}"]
```

#### 3. Performance Bottlenecks

```python
# Identify performance bottlenecks
async def identify_performance_bottlenecks(audio_data: bytes, operations: list):
    """Identify performance bottlenecks in audio processing."""

    bottleneck_analysis = {}

    for operation in operations:
        start_time = time.time()

        try:
            if operation == "vad":
                await AdvancedVADProcessor.process_audio_frame(
                    "test_session", audio_data, "test_user"
                )
            elif operation == "stt":
                request = AudioTranscriptionRequest(audio_data=audio_data, audio_format="wav")
                await stt_service.transcribe_audio(request, "performance_test")
            elif operation == "tts":
                request = SpeechSynthesisRequest(text="Performance test")
                await tts_service.generate_speech(request, "performance_test")
            elif operation == "mixing":
                await audio_mixer_service.mix_audio_streams("test_session", {"test": audio_data})

            duration = time.time() - start_time
            bottleneck_analysis[operation] = {
                "duration": duration,
                "status": "success"
            }

        except Exception as e:
            duration = time.time() - start_time
            bottleneck_analysis[operation] = {
                "duration": duration,
                "status": "error",
                "error": str(e)
            }

    # Identify bottlenecks (operations taking >1 second)
    bottlenecks = [
        op for op, analysis in bottleneck_analysis.items()
        if analysis["duration"] > 1.0
    ]

    return {
        "analysis": bottleneck_analysis,
        "bottlenecks": bottlenecks,
        "recommendations": [
            f"Optimize {bottleneck} operation" for bottleneck in bottlenecks
        ]
    }
```

#### 4. Memory Usage Issues

```python
# Monitor and manage memory usage
class AudioMemoryMonitor:
    """Monitor audio processing memory usage."""

    def __init__(self, max_memory_mb: int = 100):
        self.max_memory_mb = max_memory_mb
        self.current_usage = 0
        self.peak_usage = 0

    def track_allocation(self, size_bytes: int, operation: str):
        """Track memory allocation."""
        size_mb = size_bytes / (1024 * 1024)
        self.current_usage += size_mb
        self.peak_usage = max(self.peak_usage, self.current_usage)

        if self.current_usage > self.max_memory_mb:
            logger.warning(
                "high_memory_usage",
                current_usage_mb=self.current_usage,
                max_usage_mb=self.max_memory_mb,
                operation=operation
            )

    def track_deallocation(self, size_bytes: int):
        """Track memory deallocation."""
        size_mb = size_bytes / (1024 * 1024)
        self.current_usage = max(0, self.current_usage - size_mb)

    def get_memory_stats(self):
        """Get memory usage statistics."""
        return {
            "current_usage_mb": self.current_usage,
            "peak_usage_mb": self.peak_usage,
            "max_allowed_mb": self.max_memory_mb,
            "utilization_percent": (self.current_usage / self.max_memory_mb) * 100
        }
```

#### 5. Service Integration Issues

```python
# Troubleshoot service integration issues
async def troubleshoot_service_integration():
    """Troubleshoot integration issues between audio services."""

    integration_issues = []

    # Test service health
    services = [
        ("STT Service", stt_service.get_health_status),
        ("TTS Service", tts_service.get_health_status),
        ("Audio Processing", audio_processing_service.get_health_status),
        ("Audio Mixer", audio_mixer_service.get_health_status),
        ("VAD Processor", AdvancedVADProcessor.get_health_status),
    ]

    for service_name, health_func in services:
        try:
            health = await health_func()
            if health.get("status") != "healthy":
                integration_issues.append(f"{service_name} unhealthy: {health}")
        except Exception as e:
            integration_issues.append(f"{service_name} health check failed: {e}")

    # Test service interactions
    test_audio = b"\x00" * 16000  # 1 second of silence

    try:
        # Test STT -> TTS pipeline
        transcription_request = AudioTranscriptionRequest(
            audio_data=test_audio, audio_format="wav"
        )
        transcription = await stt_service.transcribe_audio(transcription_request, "test")

        if transcription.success:
            speech_request = SpeechSynthesisRequest(text=transcription.transcription or "test")
            speech = await tts_service.generate_speech(speech_request, "test")

            if not speech.success:
                integration_issues.append(f"STT->TTS pipeline failed: {speech.error}")
        else:
            integration_issues.append(f"STT test failed: {transcription.error}")

    except Exception as e:
        integration_issues.append(f"Service integration test failed: {e}")

    return integration_issues
```

## Security Considerations

### Audio Data Protection

```python
# Implement audio data protection
class AudioDataProtector:
    """Protect audio data during processing and storage."""

    def __init__(self):
        self.encryption_key = os.getenv("AUDIO_ENCRYPTION_KEY")

    def encrypt_audio(self, audio_data: bytes) -> bytes:
        """Encrypt audio data for storage."""
        if not self.encryption_key:
            logger.warning("No encryption key configured for audio data")
            return audio_data

        # Implement encryption (example using Fernet)
        from cryptography.fernet import Fernet
        f = Fernet(self.encryption_key)
        return f.encrypt(audio_data)

    def decrypt_audio(self, encrypted_data: bytes) -> bytes:
        """Decrypt audio data."""
        if not self.encryption_key:
            return encrypted_data

        from cryptography.fernet import Fernet
        f = Fernet(self.encryption_key)
        return f.decrypt(encrypted_data)

    def sanitize_metadata(self, metadata: dict) -> dict:
        """Sanitize metadata to remove sensitive information."""
        sensitive_keys = ["user_token", "session_secret", "private_key"]

        sanitized = {}
        for key, value in metadata.items():
            if key.lower() not in sensitive_keys:
                sanitized[key] = value
            else:
                sanitized[key] = "[REDACTED]"

        return sanitized
```

### Access Control

```python
# Implement audio access control
class AudioAccessController:
    """Control access to audio processing features."""

    def __init__(self):
        self.permissions = {
            "admin": {
                "stt": True,
                "tts": True,
                "mixing": True,
                "quality_assessment": True,
                "stream_optimization": True
            },
            "dm": {
                "stt": True,
                "tts": True,
                "mixing": True,
                "quality_assessment": True,
                "stream_optimization": False
            },
            "player": {
                "stt": True,
                "tts": False,
                "mixing": True,
                "quality_assessment": False,
                "stream_optimization": False
            }
        }

    def check_permission(self, user_role: str, feature: str) -> bool:
        """Check if user role has permission for feature."""
        role_permissions = self.permissions.get(user_role, {})
        return role_permissions.get(feature, False)

    def audit_audio_access(self, user_id: str, operation: str, audio_metadata: dict):
        """Audit audio access for security."""
        logger.info(
            "audio_access_audit",
            user_id=user_id,
            operation=operation,
            audio_size=len(audio_metadata.get("audio_data", b"")),
            audio_format=audio_metadata.get("format", "unknown"),
            correlation_id=audio_metadata.get("correlation_id", "unknown")
        )
```

This comprehensive guide covers all aspects of using the Audio Services effectively for voice interactions, audio processing, and real-time communication in the AI Dungeon Master system.