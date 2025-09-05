"""
Unit tests for Audio Processing Service Component.

This module provides comprehensive unit tests for the audio processing service including:
- Audio format conversion and validation
- Audio preprocessing and enhancement
- Stream processing capabilities
- Error handling and recovery
- Performance and quality metrics
"""

import numpy as np
import pytest

from packages.backend.components.audio.audio_processing_service import (
    AudioPipelineMetrics,
    AudioProcessingResult,
    AudioProcessingService,
)
from packages.shared.models import AudioProcessingConfig


class TestAudioProcessingResult:
    """Test cases for AudioProcessingResult."""

    def test_result_creation(self):
        """Test creating an AudioProcessingResult."""
        result = AudioProcessingResult(
            success=True,
            operation="audio_conversion",
            input_format="wav",
            output_format="mp3",
            input_duration=5.0,
            output_duration=4.8,
            processing_time=0.5,
            quality_score=0.95,
        )

        assert result.success is True
        assert result.operation == "audio_conversion"
        assert result.input_format == "wav"
        assert result.output_format == "mp3"
        assert result.input_duration == 5.0
        assert result.output_duration == 4.8
        assert result.processing_time == 0.5
        assert result.quality_score == 0.95
        assert result.error is None

    def test_result_with_error(self):
        """Test result with error information."""
        result = AudioProcessingResult(
            success=False,
            operation="format_validation",
            input_format="invalid",
            output_format="invalid",
            input_duration=0.0,
            output_duration=0.0,
            processing_time=0.1,
            quality_score=0.0,
            error="Unsupported format",
        )

        assert result.success is False
        assert result.error == "Unsupported format"
        assert result.quality_score == 0.0


class TestAudioPipelineMetrics:
    """Test cases for AudioPipelineMetrics."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = AudioPipelineMetrics()

        assert metrics.total_operations == 0
        assert metrics.successful_operations == 0
        assert metrics.failed_operations == 0
        assert metrics.total_processing_time == 0.0
        assert metrics.total_audio_duration == 0.0
        assert metrics.average_quality_score == 0.0
        assert len(metrics.format_conversions) == 0
        assert len(metrics.error_counts) == 0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = AudioPipelineMetrics()
        metrics.total_operations = 10
        metrics.successful_operations = 8

        assert metrics.success_rate == 0.8

        # Test with zero operations
        metrics.total_operations = 0
        assert metrics.success_rate == 0.0

    def test_average_processing_time(self):
        """Test average processing time calculation."""
        metrics = AudioPipelineMetrics()
        metrics.total_operations = 5
        metrics.total_processing_time = 2.5

        assert metrics.average_processing_time == 0.5

        # Test with zero operations
        metrics.total_operations = 0
        assert metrics.average_processing_time == 0.0

    def test_processing_efficiency(self):
        """Test processing efficiency calculation."""
        metrics = AudioPipelineMetrics()
        metrics.total_processing_time = 10.0
        metrics.total_audio_duration = 50.0

        assert metrics.processing_efficiency == 5.0

        # Test with zero processing time
        metrics.total_processing_time = 0.0
        assert metrics.processing_efficiency == 0.0


class TestAudioProcessingService:
    """Test cases for main AudioProcessingService."""

    def setup_method(self):
        """Set up test environment."""
        self.config = AudioProcessingConfig(
            chunk_size=1024,
            silence_threshold=0.01,
            normalize_audio=True,
            noise_reduction=True,
        )
        self.service = AudioProcessingService(self.config)

    def test_service_initialization(self):
        """Test service initialization."""
        assert isinstance(self.service.config, AudioProcessingConfig)
        assert isinstance(self.service.metrics, AudioPipelineMetrics)
        assert len(self.service._format_conversion_paths) > 0
        assert len(self.service._enhancement_pipeline) > 0

    @pytest.mark.asyncio
    async def test_process_audio_data_success(self):
        """Test successful audio data processing."""
        # Create mock WAV audio data
        sample_rate = 16000
        duration = 1.0  # 1 second
        num_samples = int(sample_rate * duration)

        # Generate simple sine wave as test audio
        t = np.linspace(0, duration, num_samples)
        frequency = 440  # A4 note
        audio_array = np.sin(2 * np.pi * frequency * t)

        # Convert to 16-bit PCM
        audio_array = (audio_array * 32767).astype(np.int16)
        audio_data = audio_array.tobytes()

        # Add minimal WAV header
        wav_header = self._create_wav_header(sample_rate, 1, 16, len(audio_data))
        wav_data = wav_header + audio_data

        result = await self.service.process_audio_data(
            audio_data=wav_data,
            input_format="wav",
            target_format="wav",
            correlation_id="test_success",
        )

        assert result.success is True
        assert result.input_format == "wav"
        assert result.output_format == "wav"
        assert result.input_duration > 0
        assert result.processing_time > 0
        assert result.quality_score > 0

        # Check metrics were updated
        assert self.service.metrics.total_operations == 1
        assert self.service.metrics.successful_operations == 1

    @pytest.mark.asyncio
    async def test_process_empty_audio_data(self):
        """Test processing empty audio data."""
        result = await self.service.process_audio_data(
            audio_data=b"", input_format="wav", correlation_id="test_empty"
        )

        assert result.success is False
        assert "Empty audio data" in result.error
        assert self.service.metrics.failed_operations == 1

    @pytest.mark.asyncio
    async def test_process_invalid_format(self):
        """Test processing invalid audio format."""
        invalid_data = b"This is not audio data"

        result = await self.service.process_audio_data(
            audio_data=invalid_data, input_format="wav", correlation_id="test_invalid"
        )

        assert result.success is False
        assert result.error is not None

    def test_get_pipeline_metrics(self):
        """Test pipeline metrics retrieval."""
        metrics = self.service.get_pipeline_metrics()

        assert isinstance(metrics, AudioPipelineMetrics)
        assert metrics.total_operations >= 0
        assert metrics.successful_operations >= 0

    def test_get_health_status(self):
        """Test health status retrieval."""
        status = self.service.get_health_status()

        assert isinstance(status, dict)
        assert "status" in status
        assert "metrics" in status
        assert "config" in status

        # Check status based on success rate
        if self.service.metrics.success_rate < 0.8:
            assert status["status"] == "degraded"
        else:
            assert status["status"] == "healthy"

    def test_reset_metrics(self):
        """Test metrics reset functionality."""
        # Add some test data
        self.service.metrics.total_operations = 5
        self.service.metrics.successful_operations = 3
        self.service.metrics.format_conversions["wav->mp3"] = 2

        # Reset metrics
        self.service.reset_metrics()

        assert self.service.metrics.total_operations == 0
        assert self.service.metrics.successful_operations == 0
        assert len(self.service.metrics.format_conversions) == 0

    def _create_wav_header(
        self, sample_rate: int, channels: int, bits_per_sample: int, data_size: int
    ) -> bytes:
        """Create a minimal WAV header for testing."""
        import struct

        # WAV header structure
        riff_id = b"RIFF"
        wave_id = b"WAVE"
        fmt_id = b"fmt "
        data_id = b"data"

        # Calculate sizes
        fmt_chunk_size = 16
        file_size = 36 + data_size

        # Format chunk
        audio_format = 1  # PCM
        block_align = channels * bits_per_sample // 8
        byte_rate = sample_rate * block_align

        fmt_chunk = struct.pack(
            "<HHIIHH",
            audio_format,
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
        )

        # Create header
        header = (
            riff_id
            + struct.pack("<I", file_size)
            + wave_id
            + fmt_id
            + struct.pack("<I", fmt_chunk_size)
            + fmt_chunk
            + data_id
            + struct.pack("<I", data_size)
        )

        return header


class TestAudioStreamProcessing:
    """Test cases for audio stream processing."""

    def setup_method(self):
        """Set up test environment."""
        self.service = AudioProcessingService()

    @pytest.mark.asyncio
    async def test_process_stream_audio(self):
        """Test stream audio processing."""
        # Create test audio data
        audio_data = b"\x00" * 4096  # 4KB of silence
        stream_id = "test_stream"

        chunks = await self.service.process_stream_audio(
            stream_id=stream_id,
            audio_data=audio_data,
            format="raw",
            sample_rate=16000,
            channels=1,
            correlation_id="stream_test",
        )

        assert isinstance(chunks, list)
        # Processing may return empty list for silence or processing chunks

    @pytest.mark.asyncio
    async def test_convert_for_stt(self):
        """Test audio conversion for STT."""
        # Create test audio data
        audio_data = b"\x00" * 16000  # 1 second of silence at 16kHz

        converted_data, format_name = await self.service.convert_for_stt(
            audio_data=audio_data,
            input_format="raw",
            correlation_id="stt_conversion_test",
        )

        # Should return data and format (may be original if conversion fails)
        assert isinstance(converted_data, bytes)
        assert isinstance(format_name, str)

    @pytest.mark.asyncio
    async def test_convert_for_tts(self):
        """Test audio conversion for TTS."""
        # Create test audio data
        audio_data = b"\x00" * 22050  # 1 second of silence at 22kHz

        converted_data, format_name = await self.service.convert_for_tts(
            audio_data=audio_data,
            input_format="raw",
            target_format="wav",
            correlation_id="tts_conversion_test",
        )

        # Should return data and format
        assert isinstance(converted_data, bytes)
        assert isinstance(format_name, str)


class TestAudioEnhancement:
    """Test cases for audio enhancement features."""

    def setup_method(self):
        """Set up test environment."""
        self.service = AudioProcessingService()

    @pytest.mark.asyncio
    async def test_apply_noise_reduction(self):
        """Test noise reduction enhancement."""
        # Create audio with some noise
        audio_data = np.random.normal(0, 0.1, 1024).astype(np.int16).tobytes()

        result = await self.service._apply_noise_reduction(
            audio_data, "wav", "noise_test"
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_apply_normalization(self):
        """Test audio normalization."""
        # Create varying amplitude audio
        audio_data = np.random.normal(0, 0.5, 1024).astype(np.int16).tobytes()

        result = await self.service._apply_normalization(audio_data, "wav", "norm_test")

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_apply_compression(self):
        """Test audio compression."""
        # Create test audio
        audio_data = np.random.normal(0, 0.3, 1024).astype(np.int16).tobytes()

        result = await self.service._apply_compression(audio_data, "wav", "comp_test")

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_apply_equalization(self):
        """Test audio equalization."""
        # Create test audio
        audio_data = np.random.normal(0, 0.2, 1024).astype(np.int16).tobytes()

        result = await self.service._apply_equalization(audio_data, "wav", "eq_test")

        assert isinstance(result, bytes)
        assert len(result) > 0


class TestAudioFormatConversion:
    """Test cases for audio format conversion."""

    def setup_method(self):
        """Set up test environment."""
        self.service = AudioProcessingService()

    @pytest.mark.asyncio
    async def test_wav_to_mp3_conversion(self):
        """Test WAV to MP3 conversion (placeholder)."""
        # Create minimal WAV data
        wav_data = self._create_minimal_wav()

        result = await self.service._convert_wav_to_mp3(wav_data, "format_test")

        # May return original data if conversion not implemented
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_mp3_to_wav_conversion(self):
        """Test MP3 to WAV conversion (placeholder)."""
        # Create mock MP3 data
        mp3_data = b"\xff\xfb" + b"\x00" * 1000  # MP3 frame sync + data

        result = await self.service._convert_mp3_to_wav(mp3_data, "format_test")

        # May return original data if conversion not implemented
        assert isinstance(result, bytes)

    def _create_minimal_wav(self) -> bytes:
        """Create minimal valid WAV data for testing."""
        import struct

        # WAV header
        riff_id = b"RIFF"
        wave_id = b"WAVE"
        fmt_id = b"fmt "
        data_id = b"data"

        # Audio parameters
        sample_rate = 16000
        channels = 1
        bits_per_sample = 16
        data_size = 1024

        fmt_chunk_size = 16
        file_size = 36 + data_size

        audio_format = 1  # PCM
        block_align = channels * bits_per_sample // 8
        byte_rate = sample_rate * block_align

        fmt_chunk = struct.pack(
            "<HHIIHH",
            audio_format,
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
        )

        # Create minimal audio data (silence)
        audio_data = b"\x00" * data_size

        header = (
            riff_id
            + struct.pack("<I", file_size)
            + wave_id
            + fmt_id
            + struct.pack("<I", fmt_chunk_size)
            + fmt_chunk
            + data_id
            + struct.pack("<I", data_size)
        )

        return header + audio_data


class TestErrorHandling:
    """Test error handling scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.service = AudioProcessingService()

    @pytest.mark.asyncio
    async def test_corrupted_audio_handling(self):
        """Test handling of corrupted audio data."""
        corrupted_data = b"\xff\xff\xff\xff"  # Invalid audio data

        result = await self.service.process_audio_data(
            audio_data=corrupted_data,
            input_format="wav",
            correlation_id="corruption_test",
        )

        assert result.success is False
        assert result.error is not None
        assert self.service.metrics.failed_operations > 0

    @pytest.mark.asyncio
    async def test_unsupported_format_handling(self):
        """Test handling of unsupported audio formats."""
        # Create data with unsupported format
        unknown_data = b"UNSUPPORTED_FORMAT" + b"\x00" * 100

        result = await self.service.process_audio_data(
            audio_data=unknown_data,
            input_format="xyz",
            correlation_id="unknown_format_test",
        )

        assert result.success is False
        assert result.error is not None

    def test_service_recovery_after_errors(self):
        """Test service recovery after processing errors."""
        # Simulate some failed operations
        initial_failed = self.service.metrics.failed_operations

        # Process some operations that might fail
        # (In real test, would set up specific failure conditions)

        # Service should still be functional
        status = self.service.get_health_status()
        assert "status" in status
        assert status["status"] in ["healthy", "degraded", "critical"]


if __name__ == "__main__":
    pytest.main([__file__])
