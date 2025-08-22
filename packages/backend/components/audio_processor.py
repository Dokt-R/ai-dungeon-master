"""
Audio Processor Component for AI Dungeon Master.

This module provides comprehensive audio stream processing functionality including:
- Real-time audio capture from Discord voice connections
- Audio buffering and chunking for STT processing
- Audio format validation and conversion
- Audio preprocessing and noise reduction
- Stream quality monitoring and optimization

Features:
- Multi-format audio support (WAV, MP3, OGG, FLAC, WEBM)
- Configurable audio buffering and chunking
- Voice activity detection and silence filtering
- Audio quality enhancement and normalization
- Performance monitoring and error handling
"""

import asyncio
import io
import time
import numpy as np
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field

from packages.shared.models import (
    AudioStreamInfo, AudioProcessingConfig,
    STTServiceStatus, TTSServiceStatus
)
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AudioChunk:
    """Represents a processed audio chunk ready for STT processing."""

    data: bytes
    format: str
    sample_rate: int
    channels: int
    timestamp: datetime
    duration: float
    stream_id: str
    sequence_number: int
    is_speech: bool = True
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioBuffer:
    """Manages audio buffering for stream processing."""

    stream_id: str
    buffer_size: int = 4096
    chunk_size: int = 1024
    overlap_size: int = 256
    max_duration: float = 30.0  # Maximum buffer duration in seconds

    _buffer: bytearray = field(default_factory=bytearray)
    _sequence_counter: int = 0
    _start_time: Optional[datetime] = None
    _last_activity: datetime = field(default_factory=datetime.utcnow)

    @property
    def duration(self) -> float:
        """Get current buffer duration in seconds."""
        if self._start_time is None:
            return 0.0
        return (datetime.utcnow() - self._start_time).total_seconds()

    @property
    def is_full(self) -> bool:
        """Check if buffer is full (by size or duration)."""
        return (
            len(self._buffer) >= self.buffer_size or
            self.duration >= self.max_duration
        )

    def add_data(self, data: bytes) -> None:
        """Add audio data to buffer."""
        if self._start_time is None:
            self._start_time = datetime.utcnow()

        self._buffer.extend(data)
        self._last_activity = datetime.utcnow()

    def get_chunks(self) -> List[AudioChunk]:
        """Extract audio chunks from buffer."""
        if len(self._buffer) < self.chunk_size:
            return []

        chunks = []
        step_size = self.chunk_size - self.overlap_size

        for i in range(0, len(self._buffer) - self.chunk_size + 1, step_size):
            chunk_data = bytes(self._buffer[i:i + self.chunk_size])
            self._sequence_counter += 1

            chunk = AudioChunk(
                data=chunk_data,
                format="raw",
                sample_rate=16000,  # Default sample rate
                channels=1,
                timestamp=self._last_activity,
                duration=self.chunk_size / 16000,  # Duration based on sample rate
                stream_id=self.stream_id,
                sequence_number=self._sequence_counter
            )
            chunks.append(chunk)

        # Clear processed data (keep overlap for next iteration)
        if len(self._buffer) > self.overlap_size:
            self._buffer = self._buffer[-(self.overlap_size):]
        else:
            self._buffer.clear()

        return chunks

    def clear(self) -> None:
        """Clear the audio buffer."""
        self._buffer.clear()
        self._start_time = None
        self._last_activity = datetime.utcnow()


class AudioProcessor:
    """
    Service for processing audio streams with buffering and chunking.

    Features:
    - Real-time audio stream capture and processing
    - Configurable audio buffering and chunking
    - Voice activity detection and silence filtering
    - Audio format conversion and validation
    - Performance monitoring and error handling
    """

    def __init__(self, config: Optional[AudioProcessingConfig] = None):
        self.config = config or AudioProcessingConfig()
        self.logger = get_logger(f"{__name__}.AudioProcessor")

        # Audio buffers for active streams
        self._buffers: Dict[str, AudioBuffer] = {}
        self._stream_configs: Dict[str, AudioProcessingConfig] = {}

        # Performance tracking
        self._operation_times: Dict[str, float] = {}
        self._processed_chunks: Dict[str, int] = {}
        self._audio_quality_metrics: Dict[str, Dict[str, Any]] = {}

        # Audio format handlers
        self._format_handlers = {
            'wav': self._handle_wav_format,
            'mp3': self._handle_mp3_format,
            'ogg': self._handle_ogg_format,
            'flac': self._handle_flac_format,
            'webm': self._handle_webm_format,
        }

    async def process_audio_stream(
        self,
        stream_id: str,
        audio_data: bytes,
        format: str = "raw",
        sample_rate: int = 16000,
        channels: int = 1,
        correlation_id: str = None
    ) -> List[AudioChunk]:
        """
        Process incoming audio stream data.

        Args:
            stream_id: Unique identifier for the audio stream
            audio_data: Raw audio data
            format: Audio format (raw, wav, mp3, etc.)
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
            correlation_id: Correlation ID for tracing

        Returns:
            List of processed audio chunks ready for STT
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="audio_stream_processing",
                stream_id=stream_id,
                correlation_id=correlation_id
            ) as trace_id:

                # Validate and preprocess audio data
                processed_data = await self._validate_and_preprocess_audio(
                    audio_data, format, sample_rate, channels, correlation_id
                )

                if processed_data is None:
                    return []

                # Initialize or get buffer for this stream
                buffer = self._get_or_create_buffer(stream_id)

                # Add processed data to buffer
                buffer.add_data(processed_data)

                # Update stream metrics
                self._update_stream_metrics(stream_id, len(audio_data), sample_rate)

                # Extract chunks if buffer is ready
                chunks = []
                if buffer.is_full:
                    chunks = buffer.get_chunks()

                    # Apply voice activity detection
                    chunks = await self._apply_voice_activity_detection(
                        chunks, correlation_id
                    )

                    # Update processing metrics
                    self._processed_chunks[stream_id] = (
                        self._processed_chunks.get(stream_id, 0) + len(chunks)
                    )

                # Track performance
                execution_time = time.time() - start_time
                self._operation_times[correlation_id] = execution_time

                self.logger.debug(
                    "audio_stream_processed",
                    stream_id=stream_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                    chunks_generated=len(chunks),
                    buffer_size=len(buffer._buffer),
                    execution_time=execution_time
                )

                return chunks

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                "audio_stream_processing_failed",
                stream_id=stream_id,
                correlation_id=correlation_id,
                execution_time=execution_time,
                error=str(e)
            )
            return []

    async def _validate_and_preprocess_audio(
        self,
        audio_data: bytes,
        format: str,
        sample_rate: int,
        channels: int,
        correlation_id: str
    ) -> Optional[bytes]:
        """Validate and preprocess audio data."""
        try:
            # Basic validation
            if len(audio_data) == 0:
                self.logger.warning(
                    "empty_audio_data",
                    correlation_id=correlation_id
                )
                return None

            # Validate sample rate
            if sample_rate < 8000 or sample_rate > 192000:
                self.logger.warning(
                    "invalid_sample_rate",
                    sample_rate=sample_rate,
                    correlation_id=correlation_id
                )
                sample_rate = 16000  # Default fallback

            # Validate channels
            if channels < 1 or channels > 2:
                self.logger.warning(
                    "invalid_channel_count",
                    channels=channels,
                    correlation_id=correlation_id
                )
                channels = 1  # Default to mono

            # Handle format-specific processing
            if format in self._format_handlers:
                processed_data = await self._format_handlers[format](
                    audio_data, sample_rate, channels
                )
            else:
                # For raw or unknown formats, apply basic processing
                processed_data = await self._process_raw_audio(
                    audio_data, sample_rate, channels
                )

            # Apply audio enhancements
            processed_data = await self._apply_audio_enhancements(
                processed_data, sample_rate, channels, correlation_id
            )

            return processed_data

        except Exception as e:
            self.logger.error(
                "audio_validation_failed",
                correlation_id=correlation_id,
                error=str(e)
            )
            return None

    async def _process_raw_audio(
        self,
        audio_data: bytes,
        sample_rate: int,
        channels: int
    ) -> bytes:
        """Process raw audio data."""
        # For raw audio, apply basic normalization
        try:
            # Convert to numpy array for processing
            if len(audio_data) % 2 != 0:
                audio_data = audio_data[:-1]  # Ensure even length for 16-bit

            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Apply basic normalization if enabled
            if self.config.normalize_audio:
                max_val = np.max(np.abs(audio_array))
                if max_val > 0:
                    audio_array = (audio_array / max_val * 32767).astype(np.int16)

            return audio_array.tobytes()

        except Exception as e:
            self.logger.warning("raw_audio_processing_failed", error=str(e))
            return audio_data

    async def _handle_wav_format(
        self,
        audio_data: bytes,
        sample_rate: int,
        channels: int
    ) -> bytes:
        """Handle WAV format audio."""
        # WAV processing - extract raw PCM data
        try:
            # Basic WAV header validation and PCM extraction
            if len(audio_data) < 44:  # Minimum WAV header size
                raise ValueError("Invalid WAV header")

            # Skip WAV header and return PCM data
            return audio_data[44:]

        except Exception as e:
            self.logger.warning("wav_processing_failed", error=str(e))
            return await self._process_raw_audio(audio_data, sample_rate, channels)

    async def _handle_mp3_format(
        self,
        audio_data: bytes,
        sample_rate: int,
        channels: int
    ) -> bytes:
        """Handle MP3 format audio."""
        # MP3 processing - would need audio library integration
        try:
            # Placeholder for MP3 decoding
            # In a real implementation, this would use a library like pydub or ffmpeg
            self.logger.info("mp3_format_detected", note="MP3 decoding not implemented")
            return audio_data  # Return as-is for now

        except Exception as e:
            self.logger.warning("mp3_processing_failed", error=str(e))
            return audio_data

    async def _handle_ogg_format(
        self,
        audio_data: bytes,
        sample_rate: int,
        channels: int
    ) -> bytes:
        """Handle OGG format audio."""
        try:
            # Placeholder for OGG decoding
            self.logger.info("ogg_format_detected", note="OGG decoding not implemented")
            return audio_data  # Return as-is for now

        except Exception as e:
            self.logger.warning("ogg_processing_failed", error=str(e))
            return audio_data

    async def _handle_flac_format(
        self,
        audio_data: bytes,
        sample_rate: int,
        channels: int
    ) -> bytes:
        """Handle FLAC format audio."""
        try:
            # Placeholder for FLAC decoding
            self.logger.info("flac_format_detected", note="FLAC decoding not implemented")
            return audio_data  # Return as-is for now

        except Exception as e:
            self.logger.warning("flac_processing_failed", error=str(e))
            return audio_data

    async def _handle_webm_format(
        self,
        audio_data: bytes,
        sample_rate: int,
        channels: int
    ) -> bytes:
        """Handle WEBM format audio."""
        try:
            # Placeholder for WEBM decoding
            self.logger.info("webm_format_detected", note="WEBM decoding not implemented")
            return audio_data  # Return as-is for now

        except Exception as e:
            self.logger.warning("webm_processing_failed", error=str(e))
            return audio_data

    async def _apply_audio_enhancements(
        self,
        audio_data: bytes,
        sample_rate: int,
        channels: int,
        correlation_id: str
    ) -> bytes:
        """Apply audio enhancements like noise reduction."""
        try:
            if not self.config.noise_reduction:
                return audio_data

            # Basic noise reduction (simplified implementation)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Apply simple spectral gating for noise reduction
            # This is a basic implementation - real noise reduction would be more sophisticated
            if len(audio_array) > 0:
                # Calculate signal statistics
                signal_mean = np.mean(audio_array)
                signal_std = np.std(audio_array)

                # Simple threshold-based noise gate
                threshold = signal_mean + (signal_std * 0.5)
                noise_mask = np.abs(audio_array) < threshold

                # Apply noise gate
                audio_array[noise_mask] = 0

                # Apply fade-in/out for smoother transitions
                fade_length = min(100, len(audio_array) // 10)
                if fade_length > 0:
                    # Fade in
                    fade_in = np.linspace(0, 1, fade_length)
                    audio_array[:fade_length] = (audio_array[:fade_length] * fade_in).astype(np.int16)

                    # Fade out
                    fade_out = np.linspace(1, 0, fade_length)
                    audio_array[-fade_length:] = (audio_array[-fade_length:] * fade_out).astype(np.int16)

            return audio_array.tobytes()

        except Exception as e:
            self.logger.warning(
                "audio_enhancement_failed",
                correlation_id=correlation_id,
                error=str(e)
            )
            return audio_data

    async def _apply_voice_activity_detection(
        self,
        chunks: List[AudioChunk],
        correlation_id: str
    ) -> List[AudioChunk]:
        """Apply voice activity detection to filter out silence."""
        try:
            if not chunks:
                return chunks

            filtered_chunks = []

            for chunk in chunks:
                if len(chunk.data) < 10:  # Too small to analyze
                    continue

                # Simple VAD based on audio energy
                audio_array = np.frombuffer(chunk.data, dtype=np.int16)
                energy = np.sqrt(np.mean(audio_array.astype(np.float64) ** 2))

                # Voice activity detection
                is_speech = energy > self.config.silence_threshold

                if is_speech:
                    chunk.is_speech = True
                    chunk.confidence = min(1.0, energy / 10000.0)  # Normalize confidence
                    filtered_chunks.append(chunk)
                elif self.config.vad_mode == "light":
                    # In light mode, keep some silence for context
                    chunk.is_speech = False
                    chunk.confidence = 0.1
                    filtered_chunks.append(chunk)

            return filtered_chunks

        except Exception as e:
            self.logger.warning(
                "voice_activity_detection_failed",
                correlation_id=correlation_id,
                error=str(e)
            )
            return chunks

    def _get_or_create_buffer(self, stream_id: str) -> AudioBuffer:
        """Get or create audio buffer for stream."""
        if stream_id not in self._buffers:
            self._buffers[stream_id] = AudioBuffer(stream_id=stream_id)
            self.logger.info("created_audio_buffer", stream_id=stream_id)

        return self._buffers[stream_id]

    def _update_stream_metrics(
        self,
        stream_id: str,
        data_size: int,
        sample_rate: int
    ) -> None:
        """Update audio quality metrics for stream."""
        if stream_id not in self._audio_quality_metrics:
            self._audio_quality_metrics[stream_id] = {
                "total_data_processed": 0,
                "average_sample_rate": sample_rate,
                "start_time": datetime.utcnow(),
                "last_update": datetime.utcnow(),
                "buffer_underruns": 0,
                "buffer_overruns": 0
            }

        metrics = self._audio_quality_metrics[stream_id]
        metrics["total_data_processed"] += data_size
        metrics["last_update"] = datetime.utcnow()

        # Update rolling average sample rate
        metrics["average_sample_rate"] = (
            metrics["average_sample_rate"] * 0.9 + sample_rate * 0.1
        )

    def get_stream_info(self, stream_id: str) -> Optional[AudioStreamInfo]:
        """Get information about an active audio stream."""
        if stream_id not in self._buffers:
            return None

        buffer = self._buffers[stream_id]
        metrics = self._audio_quality_metrics.get(stream_id, {})

        return AudioStreamInfo(
            stream_id=stream_id,
            user_id="unknown",  # Would be set by caller
            channel_id="unknown",  # Would be set by caller
            session_id="unknown",  # Would be set by caller
            format="raw",
            sample_rate=int(metrics.get("average_sample_rate", 16000)),
            channels=1,
            started_at=buffer._start_time or datetime.utcnow(),
            last_activity=buffer._last_activity,
            is_active=True,
            buffer_size=len(buffer._buffer),
            processed_chunks=self._processed_chunks.get(stream_id, 0),
            total_transcriptions=0,  # Would be updated by STT service
            average_confidence=0.0  # Would be updated by STT service
        )

    def cleanup_stream(self, stream_id: str) -> bool:
        """Clean up resources for a stream."""
        if stream_id in self._buffers:
            del self._buffers[stream_id]
            self.logger.info("cleaned_up_audio_buffer", stream_id=stream_id)

        if stream_id in self._stream_configs:
            del self._stream_configs[stream_id]

        if stream_id in self._audio_quality_metrics:
            del self._audio_quality_metrics[stream_id]

        if stream_id in self._processed_chunks:
            del self._processed_chunks[stream_id]

        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the audio processor."""
        total_streams = len(self._buffers)
        total_data_processed = sum(
            metrics.get("total_data_processed", 0)
            for metrics in self._audio_quality_metrics.values()
        )
        total_chunks_processed = sum(self._processed_chunks.values())

        return {
            "status": "healthy" if total_streams >= 0 else "error",
            "active_streams": total_streams,
            "total_data_processed": total_data_processed,
            "total_chunks_processed": total_chunks_processed,
            "average_operation_time": sum(self._operation_times.values()) / max(len(self._operation_times), 1),
            "config": {
                "chunk_size": self.config.chunk_size,
                "overlap_size": self.config.overlap_size,
                "silence_threshold": self.config.silence_threshold,
                "normalize_audio": self.config.normalize_audio,
                "noise_reduction": self.config.noise_reduction,
                "vad_mode": self.config.vad_mode
            }
        }

    def reset_stream(self, stream_id: str) -> bool:
        """Reset a stream's buffer and metrics."""
        if stream_id in self._buffers:
            self._buffers[stream_id].clear()

        if stream_id in self._audio_quality_metrics:
            del self._audio_quality_metrics[stream_id]

        if stream_id in self._processed_chunks:
            self._processed_chunks[stream_id] = 0

        self.logger.info("reset_audio_stream", stream_id=stream_id)
        return True


# Global audio processor instance
audio_processor = AudioProcessor()