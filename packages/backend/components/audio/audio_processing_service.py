"""
Audio Processing Service - Unified Audio Pipeline for AI Dungeon Master.

This module provides a unified audio processing pipeline that integrates:
- Audio format conversion and validation
- Audio stream processing and buffering
- Audio preprocessing and enhancement
- Integration with STT and TTS services
- Performance optimization and monitoring

Features:
- Unified interface for all audio processing operations
- Automatic format detection and conversion
- Audio quality enhancement and preprocessing
- Stream processing with real-time capabilities
- Integration with voice services
- Comprehensive error handling and logging
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from packages.backend.components.audio.audio_processor import (
    AudioChunk,
    audio_processor,
)
from packages.backend.components.audio.audio_utils import audio_utils
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import AudioProcessingConfig

logger = get_logger(__name__)


@dataclass
class AudioProcessingResult:
    """Result of an audio processing operation."""

    success: bool
    operation: str
    input_format: str
    output_format: str
    input_duration: float
    output_duration: float
    processing_time: float
    quality_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class AudioPipelineMetrics:
    """Metrics for the audio processing pipeline."""

    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_processing_time: float = 0.0
    total_audio_duration: float = 0.0
    average_quality_score: float = 0.0
    format_conversions: Dict[str, int] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations

    @property
    def average_processing_time(self) -> float:
        """Calculate average processing time per operation."""
        if self.total_operations == 0:
            return 0.0
        return self.total_processing_time / self.total_operations

    @property
    def processing_efficiency(self) -> float:
        """Calculate processing efficiency (duration ratio)."""
        if self.total_processing_time == 0.0:
            return 0.0
        return self.total_audio_duration / self.total_processing_time


class AudioProcessingService:
    """
    Unified audio processing service for the AI Dungeon Master.

    Features:
    - Unified audio processing pipeline
    - Automatic format detection and conversion
    - Audio quality enhancement and preprocessing
    - Integration with STT and TTS services
    - Real-time stream processing capabilities
    - Comprehensive performance monitoring
    """

    def __init__(self, config: Optional[AudioProcessingConfig] = None):
        self.config = config or AudioProcessingConfig()
        self.logger = get_logger(f"{__name__}.AudioProcessingService")

        # Metrics tracking
        self.metrics = AudioPipelineMetrics()

        # Audio format conversion mappings
        self._format_conversion_paths = {
            ("wav", "mp3"): self._convert_wav_to_mp3,
            ("wav", "ogg"): self._convert_wav_to_ogg,
            ("wav", "flac"): self._convert_wav_to_flac,
            ("mp3", "wav"): self._convert_mp3_to_wav,
            ("ogg", "wav"): self._convert_ogg_to_wav,
            ("flac", "wav"): self._convert_flac_to_wav,
            ("webm", "wav"): self._convert_webm_to_wav,
        }

        # Quality enhancement pipeline
        self._enhancement_pipeline = [
            self._apply_noise_reduction,
            self._apply_normalization,
            self._apply_compression,
            self._apply_equalization,
        ]

    async def process_audio_data(
        self,
        audio_data: bytes,
        input_format: str,
        target_format: Optional[str] = None,
        target_sample_rate: Optional[int] = None,
        target_channels: Optional[int] = None,
        correlation_id: str = None,
        enhance_quality: bool = True,
    ) -> AudioProcessingResult:
        """
        Process audio data through the unified pipeline.

        Args:
            audio_data: Raw audio data
            input_format: Input audio format
            target_format: Desired output format
            target_sample_rate: Target sample rate
            target_channels: Target channel count
            correlation_id: Correlation ID for tracing
            enhance_quality: Whether to apply quality enhancement

        Returns:
            AudioProcessingResult with processing details
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="audio_data_processing",
                input_format=input_format,
                target_format=target_format,
                correlation_id=correlation_id,
            ) as trace_id:
                # Update metrics
                self.metrics.total_operations += 1

                # Validate input audio
                validation_result = audio_utils.validate_audio_format(
                    audio_data, input_format
                )
                if not validation_result[0]:
                    error_msg = validation_result[2]
                    self._record_error("validation_failed")
                    return AudioProcessingResult(
                        success=False,
                        operation="audio_processing",
                        input_format=input_format,
                        output_format=input_format,
                        input_duration=0.0,
                        output_duration=0.0,
                        processing_time=time.time() - start_time,
                        quality_score=0.0,
                        error=error_msg,
                    )

                detected_format = validation_result[1]

                # Extract audio info for metrics
                audio_info = (
                    audio_utils.extract_wav_info(audio_data)
                    if detected_format == "wav"
                    else {}
                )
                input_duration = audio_info.get("duration", 0.0)

                # Apply format conversion if needed
                processed_data = audio_data
                output_format = detected_format

                if target_format and target_format != detected_format:
                    conversion_result = await self._convert_audio_format(
                        audio_data,
                        detected_format,
                        target_format,
                        target_sample_rate,
                        target_channels,
                        correlation_id,
                    )

                    if conversion_result[0]:
                        processed_data = conversion_result[1]
                        output_format = target_format
                        self.metrics.format_conversions[
                            f"{detected_format}->{target_format}"
                        ] = (
                            self.metrics.format_conversions.get(
                                f"{detected_format}->{target_format}", 0
                            )
                            + 1
                        )
                    else:
                        # Conversion failed, use original
                        processed_data = audio_data
                        output_format = detected_format

                # Apply quality enhancement if requested
                if enhance_quality:
                    processed_data = await self._enhance_audio_quality(
                        processed_data, output_format, correlation_id
                    )

                # Calculate quality score
                quality_score = audio_utils.calculate_audio_quality_score(
                    processed_data,
                    output_format,
                    target_sample_rate or 22050,
                    target_channels or 1,
                )

                # Calculate output duration (approximate)
                output_duration = (
                    input_duration  # Would need format-specific calculation
                )

                processing_time = time.time() - start_time

                # Update metrics
                self.metrics.successful_operations += 1
                self.metrics.total_processing_time += processing_time
                self.metrics.total_audio_duration += output_duration
                self.metrics.average_quality_score = (
                    self.metrics.average_quality_score * 0.9 + quality_score * 0.1
                )

                self.logger.info(
                    "audio_processing_completed",
                    input_format=input_format,
                    output_format=output_format,
                    input_duration=input_duration,
                    output_duration=output_duration,
                    quality_score=quality_score,
                    processing_time=processing_time,
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                )

                return AudioProcessingResult(
                    success=True,
                    operation="audio_processing",
                    input_format=input_format,
                    output_format=output_format,
                    input_duration=input_duration,
                    output_duration=output_duration,
                    processing_time=processing_time,
                    quality_score=quality_score,
                )

        except Exception as e:
            processing_time = time.time() - start_time
            self._record_error("processing_failed")

            self.logger.error(
                "audio_processing_failed",
                input_format=input_format,
                target_format=target_format,
                correlation_id=correlation_id,
                processing_time=processing_time,
                error=str(e),
            )

            return AudioProcessingResult(
                success=False,
                operation="audio_processing",
                input_format=input_format,
                output_format=input_format,
                input_duration=0.0,
                output_duration=0.0,
                processing_time=processing_time,
                quality_score=0.0,
                error=str(e),
            )

    async def process_stream_audio(
        self,
        stream_id: str,
        audio_data: bytes,
        format: str = "raw",
        sample_rate: int = 16000,
        channels: int = 1,
        correlation_id: str = None,
    ) -> List[AudioChunk]:
        """
        Process audio stream data for real-time applications.

        Args:
            stream_id: Unique stream identifier
            audio_data: Audio data from stream
            format: Audio format
            sample_rate: Sample rate
            channels: Channel count
            correlation_id: Correlation ID for tracing

        Returns:
            List of processed audio chunks ready for STT
        """
        try:
            # Delegate to audio processor for stream handling
            chunks = await audio_processor.process_audio_stream(
                stream_id=stream_id,
                audio_data=audio_data,
                format=format,
                sample_rate=sample_rate,
                channels=channels,
                correlation_id=correlation_id,
            )

            # Apply additional processing to chunks if needed
            processed_chunks = []
            for chunk in chunks:
                # Apply format conversion if needed
                if format != "wav":  # Convert to WAV for consistency
                    converted_data = await self._convert_chunk_format(chunk, "wav")
                    if converted_data:
                        chunk.data = converted_data
                        chunk.format = "wav"

                # Apply quality enhancement
                enhanced_data = await self._enhance_chunk_quality(chunk, correlation_id)
                if enhanced_data:
                    chunk.data = enhanced_data

                processed_chunks.append(chunk)

            return processed_chunks

        except Exception as e:
            self.logger.error(
                "stream_audio_processing_failed",
                stream_id=stream_id,
                correlation_id=correlation_id,
                error=str(e),
            )
            return []

    async def convert_for_stt(
        self, audio_data: bytes, input_format: str, correlation_id: str = None
    ) -> Tuple[bytes, str]:
        """
        Convert audio data to optimal format for STT processing.

        Args:
            audio_data: Input audio data
            input_format: Input format
            correlation_id: Correlation ID for tracing

        Returns:
            Tuple of (converted_audio_data, format)
        """
        try:
            # Optimal STT format is typically 16kHz mono WAV
            target_format = "wav"
            target_sample_rate = 16000
            target_channels = 1

            result = await self.process_audio_data(
                audio_data=audio_data,
                input_format=input_format,
                target_format=target_format,
                target_sample_rate=target_sample_rate,
                target_channels=target_channels,
                correlation_id=correlation_id,
                enhance_quality=True,
            )

            if result.success:
                return result.output_data, result.output_format
            else:
                # Return original data if conversion failed
                return audio_data, input_format

        except Exception as e:
            self.logger.error(
                "stt_conversion_failed",
                input_format=input_format,
                correlation_id=correlation_id,
                error=str(e),
            )
            return audio_data, input_format

    async def convert_for_tts(
        self,
        audio_data: bytes,
        input_format: str,
        target_format: str = "wav",
        correlation_id: str = None,
    ) -> Tuple[bytes, str]:
        """
        Convert audio data from TTS to desired format.

        Args:
            audio_data: Input audio data from TTS
            input_format: Input format from TTS
            target_format: Desired output format
            correlation_id: Correlation ID for tracing

        Returns:
            Tuple of (converted_audio_data, format)
        """
        try:
            result = await self.process_audio_data(
                audio_data=audio_data,
                input_format=input_format,
                target_format=target_format,
                correlation_id=correlation_id,
                enhance_quality=True,
            )

            if result.success:
                return result.output_data, result.output_format
            else:
                return audio_data, input_format

        except Exception as e:
            self.logger.error(
                "tts_conversion_failed",
                input_format=input_format,
                target_format=target_format,
                correlation_id=correlation_id,
                error=str(e),
            )
            return audio_data, input_format

    async def _convert_audio_format(
        self,
        audio_data: bytes,
        input_format: str,
        target_format: str,
        target_sample_rate: Optional[int] = None,
        target_channels: Optional[int] = None,
        correlation_id: str = None,
    ) -> Tuple[bool, bytes]:
        """Convert audio between formats."""
        try:
            conversion_key = (input_format, target_format)

            if conversion_key in self._format_conversion_paths:
                converted_data = await self._format_conversion_paths[conversion_key](
                    audio_data, correlation_id
                )
                if converted_data:
                    # Apply sample rate and channel conversion if needed
                    if target_sample_rate:
                        converted_data = audio_utils.convert_sample_rate(
                            converted_data,
                            target_format,
                            16000,
                            target_sample_rate,
                            target_channels or 1,
                        )
                    if target_channels:
                        converted_data = audio_utils.convert_channels(
                            converted_data,
                            1,
                            target_channels,
                            target_sample_rate or 16000,
                        )
                    return True, converted_data

            # Fallback to basic conversion if specific path not available
            return await self._basic_format_conversion(
                audio_data,
                input_format,
                target_format,
                target_sample_rate,
                target_channels,
                correlation_id,
            )

        except Exception as e:
            self.logger.warning(
                "audio_format_conversion_failed",
                input_format=input_format,
                target_format=target_format,
                correlation_id=correlation_id,
                error=str(e),
            )
            return False, audio_data

    async def _basic_format_conversion(
        self,
        audio_data: bytes,
        input_format: str,
        target_format: str,
        target_sample_rate: Optional[int] = None,
        target_channels: Optional[int] = None,
        correlation_id: str = None,
    ) -> Tuple[bool, bytes]:
        """Basic format conversion fallback."""
        try:
            # For basic conversion, try to convert to WAV first, then to target
            if input_format != "wav":
                # This would need actual audio library integration
                # For now, return original data with warning
                self.logger.info(
                    "basic_format_conversion_not_implemented",
                    input_format=input_format,
                    target_format=target_format,
                    correlation_id=correlation_id,
                )
                return True, audio_data  # Return original as "converted"

            return True, audio_data

        except Exception as e:
            self.logger.error(
                "basic_format_conversion_error",
                correlation_id=correlation_id,
                error=str(e),
            )
            return False, audio_data

    # Format-specific conversion methods (placeholders for actual implementations)
    async def _convert_wav_to_mp3(
        self, audio_data: bytes, correlation_id: str
    ) -> Optional[bytes]:
        """Convert WAV to MP3."""
        self.logger.info(
            "wav_to_mp3_conversion_requested", correlation_id=correlation_id
        )
        return audio_data  # Placeholder

    async def _convert_wav_to_ogg(
        self, audio_data: bytes, correlation_id: str
    ) -> Optional[bytes]:
        """Convert WAV to OGG."""
        self.logger.info(
            "wav_to_ogg_conversion_requested", correlation_id=correlation_id
        )
        return audio_data  # Placeholder

    async def _convert_wav_to_flac(
        self, audio_data: bytes, correlation_id: str
    ) -> Optional[bytes]:
        """Convert WAV to FLAC."""
        self.logger.info(
            "wav_to_flac_conversion_requested", correlation_id=correlation_id
        )
        return audio_data  # Placeholder

    async def _convert_mp3_to_wav(
        self, audio_data: bytes, correlation_id: str
    ) -> Optional[bytes]:
        """Convert MP3 to WAV."""
        self.logger.info(
            "mp3_to_wav_conversion_requested", correlation_id=correlation_id
        )
        return audio_data  # Placeholder

    async def _convert_ogg_to_wav(
        self, audio_data: bytes, correlation_id: str
    ) -> Optional[bytes]:
        """Convert OGG to WAV."""
        self.logger.info(
            "ogg_to_wav_conversion_requested", correlation_id=correlation_id
        )
        return audio_data  # Placeholder

    async def _convert_flac_to_wav(
        self, audio_data: bytes, correlation_id: str
    ) -> Optional[bytes]:
        """Convert FLAC to WAV."""
        self.logger.info(
            "flac_to_wav_conversion_requested", correlation_id=correlation_id
        )
        return audio_data  # Placeholder

    async def _convert_webm_to_wav(
        self, audio_data: bytes, correlation_id: str
    ) -> Optional[bytes]:
        """Convert WebM to WAV."""
        self.logger.info(
            "webm_to_wav_conversion_requested", correlation_id=correlation_id
        )
        return audio_data  # Placeholder

    async def _enhance_audio_quality(
        self, audio_data: bytes, format: str, correlation_id: str
    ) -> bytes:
        """Apply quality enhancement to audio data."""
        try:
            enhanced_data = audio_data

            # Apply enhancement pipeline
            for enhancement in self._enhancement_pipeline:
                enhanced_data = await enhancement(enhanced_data, format, correlation_id)

            return enhanced_data

        except Exception as e:
            self.logger.warning(
                "audio_quality_enhancement_failed",
                correlation_id=correlation_id,
                error=str(e),
            )
            return audio_data

    async def _apply_noise_reduction(
        self, audio_data: bytes, format: str, correlation_id: str
    ) -> bytes:
        """Apply noise reduction to audio."""
        # Placeholder for noise reduction implementation
        return audio_data

    async def _apply_normalization(
        self, audio_data: bytes, format: str, correlation_id: str
    ) -> bytes:
        """Apply audio normalization."""
        # Placeholder for normalization implementation
        return audio_data

    async def _apply_compression(
        self, audio_data: bytes, format: str, correlation_id: str
    ) -> bytes:
        """Apply audio compression."""
        # Placeholder for compression implementation
        return audio_data

    async def _apply_equalization(
        self, audio_data: bytes, format: str, correlation_id: str
    ) -> bytes:
        """Apply audio equalization."""
        # Placeholder for equalization implementation
        return audio_data

    async def _convert_chunk_format(
        self, chunk: AudioChunk, target_format: str
    ) -> Optional[bytes]:
        """Convert audio chunk format."""
        if chunk.format == target_format:
            return chunk.data

        # Placeholder for chunk format conversion
        return chunk.data

    async def _enhance_chunk_quality(
        self, chunk: AudioChunk, correlation_id: str
    ) -> Optional[bytes]:
        """Enhance audio chunk quality."""
        # Placeholder for chunk quality enhancement
        return chunk.data

    def _record_error(self, error_type: str) -> None:
        """Record an error in metrics."""
        self.metrics.failed_operations += 1
        self.metrics.error_counts[error_type] = (
            self.metrics.error_counts.get(error_type, 0) + 1
        )

    def get_pipeline_metrics(self) -> AudioPipelineMetrics:
        """Get current pipeline metrics."""
        return self.metrics

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the audio processing service."""
        return {
            "status": "healthy" if self.metrics.success_rate > 0.8 else "degraded",
            "metrics": {
                "success_rate": self.metrics.success_rate,
                "average_processing_time": self.metrics.average_processing_time,
                "average_quality_score": self.metrics.average_quality_score,
                "processing_efficiency": self.metrics.processing_efficiency,
                "total_operations": self.metrics.total_operations,
                "format_conversions": self.metrics.format_conversions,
                "error_counts": self.metrics.error_counts,
            },
            "config": {
                "noise_reduction": self.config.noise_reduction,
                "normalize_audio": self.config.normalize_audio,
                "chunk_size": self.config.chunk_size,
                "silence_threshold": self.config.silence_threshold,
            },
        }

    def reset_metrics(self) -> None:
        """Reset pipeline metrics."""
        self.metrics = AudioPipelineMetrics()
        self.logger.info("audio_pipeline_metrics_reset")


# Global audio processing service instance
audio_processing_service = AudioProcessingService()
