"""
Audio Utilities for AI Dungeon Master.

This module provides utility functions for audio format conversion, validation,
and preprocessing. It serves as a bridge between the audio processor and
external audio processing libraries.

Features:
- Audio format detection and validation
- Format conversion between common audio formats
- Audio quality validation and enhancement
- Sample rate and channel conversion
- Audio metadata extraction
"""

import io
import wave
import struct
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioFormatInfo:
    """Information about an audio format and its properties."""

    format_name: str
    mime_type: str
    extensions: list[str]
    supports_compression: bool
    max_sample_rate: int
    min_sample_rate: int
    supported_channels: list[int]
    description: str


# Supported audio formats
SUPPORTED_FORMATS = {
    'wav': AudioFormatInfo(
        format_name='WAV',
        mime_type='audio/wav',
        extensions=['.wav'],
        supports_compression=False,
        max_sample_rate=192000,
        min_sample_rate=8000,
        supported_channels=[1, 2],
        description='Uncompressed PCM audio format'
    ),
    'mp3': AudioFormatInfo(
        format_name='MP3',
        mime_type='audio/mpeg',
        extensions=['.mp3'],
        supports_compression=True,
        max_sample_rate=48000,
        min_sample_rate=8000,
        supported_channels=[1, 2],
        description='MPEG-1 Audio Layer III compressed format'
    ),
    'ogg': AudioFormatInfo(
        format_name='OGG',
        mime_type='audio/ogg',
        extensions=['.ogg', '.oga'],
        supports_compression=True,
        max_sample_rate=192000,
        min_sample_rate=8000,
        supported_channels=[1, 2, 4, 5, 6, 7, 8],
        description='Ogg Vorbis compressed format'
    ),
    'flac': AudioFormatInfo(
        format_name='FLAC',
        mime_type='audio/flac',
        extensions=['.flac'],
        supports_compression=True,
        max_sample_rate=192000,
        min_sample_rate=8000,
        supported_channels=[1, 2, 4, 5, 6, 7, 8],
        description='Free Lossless Audio Codec'
    ),
    'webm': AudioFormatInfo(
        format_name='WEBM',
        mime_type='audio/webm',
        extensions=['.webm'],
        supports_compression=True,
        max_sample_rate=48000,
        min_sample_rate=8000,
        supported_channels=[1, 2],
        description='WebM audio format with Vorbis/Opus codec'
    )
}


class AudioUtils:
    """
    Utility class for audio format conversion and validation.

    This class provides static methods for:
    - Audio format detection and validation
    - Format conversion between supported formats
    - Audio quality assessment
    - Sample rate and channel conversion
    """

    @staticmethod
    def detect_audio_format(audio_data: bytes) -> Optional[str]:
        """
        Detect audio format from raw audio data.

        Args:
            audio_data: Raw audio data bytes

        Returns:
            Format string or None if detection fails
        """
        if len(audio_data) < 12:
            return None

        # Check for WAV header
        if audio_data.startswith(b'RIFF') and b'WAVE' in audio_data[8:12]:
            return 'wav'

        # Check for MP3 frame sync
        if len(audio_data) >= 4:
            # MP3 frames start with sync bits (11 bits set to 1)
            first_word = struct.unpack('>H', audio_data[:2])[0]
            if (first_word & 0xFFE0) == 0xFFE0:  # Frame sync pattern
                return 'mp3'

        # Check for OGG container
        if audio_data.startswith(b'OggS'):
            return 'ogg'

        # Check for FLAC signature
        if audio_data.startswith(b'fLaC'):
            return 'flac'

        # Check for WebM/Matroska
        if audio_data.startswith(b'\x1a\x45\xdf\xa3'):
            return 'webm'

        return None

    @staticmethod
    def validate_audio_format(
        audio_data: bytes,
        expected_format: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate audio data format and quality.

        Args:
            audio_data: Raw audio data bytes
            expected_format: Expected format string or None

        Returns:
            Tuple of (is_valid, detected_format, error_message)
        """
        try:
            if len(audio_data) == 0:
                return False, None, "Empty audio data"

            detected_format = AudioUtils.detect_audio_format(audio_data)

            if detected_format is None:
                return False, None, "Unknown or unsupported audio format"

            if expected_format and detected_format != expected_format:
                return False, detected_format, f"Format mismatch: expected {expected_format}, got {detected_format}"

            # Format-specific validation
            if detected_format == 'wav':
                return AudioUtils._validate_wav_data(audio_data)
            elif detected_format == 'mp3':
                return AudioUtils._validate_mp3_data(audio_data)
            elif detected_format == 'ogg':
                return AudioUtils._validate_ogg_data(audio_data)
            elif detected_format == 'flac':
                return AudioUtils._validate_flac_data(audio_data)
            elif detected_format == 'webm':
                return AudioUtils._validate_webm_data(audio_data)

            return True, detected_format, None

        except Exception as e:
            return False, None, f"Validation error: {str(e)}"

    @staticmethod
    def _validate_wav_data(audio_data: bytes) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate WAV audio data."""
        try:
            if len(audio_data) < 44:  # Minimum WAV header size
                return False, 'wav', "WAV header too small"

            # Parse WAV header
            riff_id = audio_data[0:4]
            if riff_id != b'RIFF':
                return False, 'wav', "Invalid RIFF header"

            wave_id = audio_data[8:12]
            if wave_id != b'WAVE':
                return False, 'wav', "Invalid WAVE header"

            # Extract basic format info
            format_tag = struct.unpack('<H', audio_data[20:22])[0]
            channels = struct.unpack('<H', audio_data[22:24])[0]
            sample_rate = struct.unpack('<I', audio_data[24:28])[0]
            bits_per_sample = struct.unpack('<H', audio_data[34:36])[0]

            # Validate parameters
            format_info = SUPPORTED_FORMATS['wav']
            if sample_rate < format_info.min_sample_rate or sample_rate > format_info.max_sample_rate:
                return False, 'wav', f"Sample rate {sample_rate} Hz not supported"

            if channels not in format_info.supported_channels:
                return False, 'wav', f"Channel count {channels} not supported"

            if format_tag != 1:  # PCM format
                return False, 'wav', f"Unsupported format tag {format_tag} (only PCM supported)"

            return True, 'wav', None

        except Exception as e:
            return False, 'wav', f"WAV validation error: {str(e)}"

    @staticmethod
    def _validate_mp3_data(audio_data: bytes) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate MP3 audio data."""
        try:
            # Basic MP3 validation - check for valid frame headers
            if len(audio_data) < 4:
                return False, 'mp3', "MP3 data too small"

            # Look for MP3 frame sync pattern
            found_valid_frame = False
            for i in range(len(audio_data) - 3):
                if (audio_data[i] & 0xFF) == 0xFF and (audio_data[i + 1] & 0xE0) == 0xE0:
                    found_valid_frame = True
                    break

            if not found_valid_frame:
                return False, 'mp3', "No valid MP3 frame found"

            return True, 'mp3', None

        except Exception as e:
            return False, 'mp3', f"MP3 validation error: {str(e)}"

    @staticmethod
    def _validate_ogg_data(audio_data: bytes) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate OGG audio data."""
        try:
            if len(audio_data) < 27:  # Minimum OGG header size
                return False, 'ogg', "OGG data too small"

            if not audio_data.startswith(b'OggS'):
                return False, 'ogg', "Invalid OGG signature"

            # Basic OGG page validation
            version = audio_data[4]
            if version != 0:
                return False, 'ogg', f"Unsupported OGG version {version}"

            return True, 'ogg', None

        except Exception as e:
            return False, 'ogg', f"OGG validation error: {str(e)}"

    @staticmethod
    def _validate_flac_data(audio_data: bytes) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate FLAC audio data."""
        try:
            if len(audio_data) < 8:
                return False, 'flac', "FLAC data too small"

            if not audio_data.startswith(b'fLaC'):
                return False, 'flac', "Invalid FLAC signature"

            return True, 'flac', None

        except Exception as e:
            return False, 'flac', f"FLAC validation error: {str(e)}"

    @staticmethod
    def _validate_webm_data(audio_data: bytes) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate WebM audio data."""
        try:
            if len(audio_data) < 4:
                return False, 'webm', "WebM data too small"

            if not audio_data.startswith(b'\x1a\x45\xdf\xa3'):
                return False, 'webm', "Invalid WebM signature"

            return True, 'webm', None

        except Exception as e:
            return False, 'webm', f"WebM validation error: {str(e)}"

    @staticmethod
    def extract_wav_info(audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Extract audio information from WAV data."""
        try:
            if len(audio_data) < 44:
                return None

            # Parse WAV header
            channels = struct.unpack('<H', audio_data[22:24])[0]
            sample_rate = struct.unpack('<I', audio_data[24:28])[0]
            bits_per_sample = struct.unpack('<H', audio_data[34:36])[0]
            data_size = struct.unpack('<I', audio_data[40:44])[0]

            return {
                'format': 'wav',
                'channels': channels,
                'sample_rate': sample_rate,
                'bits_per_sample': bits_per_sample,
                'data_size': data_size,
                'duration': data_size / (sample_rate * channels * (bits_per_sample // 8))
            }

        except Exception as e:
            logger.warning("Failed to extract WAV info", error=str(e))
            return None

    @staticmethod
    def convert_sample_rate(
        audio_data: bytes,
        input_format: str,
        input_sample_rate: int,
        output_sample_rate: int,
        channels: int = 1
    ) -> Optional[bytes]:
        """
        Convert audio sample rate.

        This is a simplified implementation. In production, you would use
        a proper audio processing library like librosa, pydub, or ffmpeg.
        """
        try:
            if input_format != 'wav':
                # For non-WAV formats, return as-is (would need format-specific handling)
                return audio_data

            if input_sample_rate == output_sample_rate:
                return audio_data

            # Simple sample rate conversion (basic linear interpolation)
            import numpy as np

            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Calculate conversion ratio
            ratio = output_sample_rate / input_sample_rate

            # Generate new sample indices
            old_indices = np.arange(len(audio_array))
            new_length = int(len(audio_array) * ratio)
            new_indices = np.linspace(0, len(audio_array) - 1, new_length)

            # Linear interpolation
            converted_audio = np.interp(new_indices, old_indices, audio_array)

            # Convert back to bytes
            return converted_audio.astype(np.int16).tobytes()

        except Exception as e:
            logger.error("Sample rate conversion failed", error=str(e))
            return None

    @staticmethod
    def convert_channels(
        audio_data: bytes,
        input_channels: int,
        output_channels: int,
        sample_rate: int = 16000
    ) -> Optional[bytes]:
        """
        Convert audio channel count.

        This is a simplified implementation. In production, you would use
        a proper audio processing library.
        """
        try:
            if input_channels == output_channels:
                return audio_data

            # Simple channel conversion
            import numpy as np

            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            if input_channels == 1 and output_channels == 2:
                # Mono to stereo
                converted_audio = np.column_stack((audio_array, audio_array)).flatten()
            elif input_channels == 2 and output_channels == 1:
                # Stereo to mono (average channels)
                audio_2d = audio_array.reshape(-1, 2)
                converted_audio = np.mean(audio_2d, axis=1).astype(np.int16)
            else:
                # Unsupported conversion
                return audio_data

            return converted_audio.tobytes()

        except Exception as e:
            logger.error("Channel conversion failed", error=str(e))
            return None

    @staticmethod
    def get_supported_formats() -> Dict[str, AudioFormatInfo]:
        """Get information about all supported audio formats."""
        return SUPPORTED_FORMATS.copy()

    @staticmethod
    def is_format_supported(format_name: str) -> bool:
        """Check if an audio format is supported."""
        return format_name.lower() in SUPPORTED_FORMATS

    @staticmethod
    def get_format_info(format_name: str) -> Optional[AudioFormatInfo]:
        """Get information about a specific audio format."""
        return SUPPORTED_FORMATS.get(format_name.lower())

    @staticmethod
    def calculate_audio_quality_score(
        audio_data: bytes,
        format_name: str,
        sample_rate: int,
        channels: int
    ) -> float:
        """
        Calculate a quality score for audio data.

        Returns a score between 0.0 and 1.0 based on:
        - Format quality (lossless vs lossy)
        - Sample rate appropriateness
        - Channel configuration
        - Data integrity
        """
        try:
            score = 1.0

            # Format quality factor
            if format_name in ['flac', 'wav']:
                score *= 1.0  # Lossless formats
            elif format_name in ['ogg', 'webm']:
                score *= 0.9  # High-quality lossy
            elif format_name == 'mp3':
                score *= 0.8  # Standard lossy

            # Sample rate factor
            if sample_rate >= 44100:
                score *= 1.0
            elif sample_rate >= 22050:
                score *= 0.9
            elif sample_rate >= 16000:
                score *= 0.8
            else:
                score *= 0.6

            # Channel factor
            if channels == 2:
                score *= 1.0
            elif channels == 1:
                score *= 0.9
            else:
                score *= 0.7  # Multi-channel

            # Data integrity check
            if len(audio_data) == 0:
                score *= 0.1

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.warning("Quality score calculation failed", error=str(e))
            return 0.5  # Neutral score on error


# Global audio utils instance
audio_utils = AudioUtils()