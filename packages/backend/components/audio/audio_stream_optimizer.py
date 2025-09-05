"""
Audio Stream Optimizer Component for AI Dungeon Master.

This module provides optimized audio streaming and real-time processing capabilities
to meet the 4-second NFR1 latency target through intelligent buffering, parallel processing,
and predictive audio generation.

Features:
- Predictive audio buffering for reduced latency
- Parallel STT and AI processing pipelines
- Streaming audio optimization for Discord voice
- Real-time audio preprocessing and enhancement
- Adaptive buffering based on network conditions
- Preemptive TTS generation for common responses
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from packages.backend.components.observability_service import observability_service
from packages.backend.components.audio.tts_service import tts_service
from packages.backend.components.audio.voice_performance_monitor import (
    voice_performance_monitor,
)
from packages.shared.logging_config import get_logger
from packages.shared.models import (
    AudioStreamInfo,
    SpeechSynthesisResult,
    TextToSpeechRequest,
)

logger = get_logger(__name__)


@dataclass
class StreamBuffer:
    """Optimized stream buffer with predictive capabilities."""

    stream_id: str
    max_size: int = 8192
    optimal_size: int = 4096
    min_size: int = 1024
    overflow_threshold: int = 6144

    _buffer: bytearray = field(default_factory=bytearray)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _last_access: datetime = field(default_factory=datetime.utcnow)
    _overflow_count: int = 0

    @property
    def size(self) -> int:
        """Get current buffer size."""
        with self._lock:
            return len(self._buffer)

    @property
    def utilization(self) -> float:
        """Get buffer utilization percentage."""
        return (self.size / self.max_size) * 100.0

    def add_data(self, data: bytes) -> bool:
        """Add data to buffer with overflow protection."""
        with self._lock:
            if len(self._buffer) + len(data) > self.max_size:
                # Buffer overflow - remove oldest data to make space
                overflow_amount = len(self._buffer) + len(data) - self.max_size
                self._buffer = self._buffer[overflow_amount:]
                self._overflow_count += 1
                logger.warning(
                    "stream_buffer_overflow",
                    stream_id=self.stream_id,
                    overflow_amount=overflow_amount,
                    overflow_count=self._overflow_count,
                )
                return False

            self._buffer.extend(data)
            self._last_access = datetime.utcnow()
            return True

    def get_data(self, size: int) -> Optional[bytes]:
        """Get data from buffer."""
        with self._lock:
            if len(self._buffer) < size:
                return None

            data = bytes(self._buffer[:size])
            self._buffer = self._buffer[size:]
            self._last_access = datetime.utcnow()
            return data

    def peek_data(self, size: int) -> Optional[bytes]:
        """Peek at data without removing it."""
        with self._lock:
            if len(self._buffer) < size:
                return None
            return bytes(self._buffer[:size])

    def clear(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._buffer.clear()
            self._last_access = datetime.utcnow()


@dataclass
class ProcessingPipeline:
    """Represents a processing pipeline with parallel execution."""

    pipeline_id: str
    stages: List[Callable] = field(default_factory=list)
    timeout: float = 30.0
    max_concurrent: int = 3

    _semaphore: asyncio.Semaphore = None

    def __post_init__(self):
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> Any:
        """Execute the processing pipeline."""
        async with self._semaphore:
            try:
                result = input_data
                pipeline_context = context or {}

                for stage in self.stages:
                    start_time = time.time()

                    # Execute stage with timeout
                    result = await asyncio.wait_for(
                        stage(result, pipeline_context), timeout=self.timeout
                    )

                    stage_time = time.time() - start_time
                    pipeline_context[f"stage_time_{stage.__name__}"] = stage_time

                return result

            except asyncio.TimeoutError:
                logger.error(
                    "pipeline_stage_timeout",
                    pipeline_id=self.pipeline_id,
                    timeout=self.timeout,
                )
                raise
            except Exception as e:
                logger.error(
                    "pipeline_execution_error",
                    pipeline_id=self.pipeline_id,
                    error=str(e),
                )
                raise


@dataclass
class PredictiveCache:
    """Predictive caching for common voice interactions."""

    max_entries: int = 100
    cache_ttl: timedelta = timedelta(hours=1)

    _cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _access_times: Dict[str, datetime] = field(default_factory=dict)

    def add_prediction(self, key: str, prediction: Dict[str, Any]) -> None:
        """Add a prediction to the cache."""
        if len(self._cache) >= self.max_entries:
            self._evict_oldest()

        self._cache[key] = prediction
        self._access_times[key] = datetime.utcnow()

    def get_prediction(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a prediction from the cache."""
        if key not in self._cache:
            return None

        # Check if expired
        if datetime.utcnow() - self._access_times[key] > self.cache_ttl:
            del self._cache[key]
            del self._access_times[key]
            return None

        self._access_times[key] = datetime.utcnow()
        return self._cache[key]

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry."""
        if not self._access_times:
            return

        oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        del self._cache[oldest_key]
        del self._access_times[oldest_key]


class AudioStreamOptimizer:
    """
    Optimized audio streaming and real-time processing.

    Features:
    - Predictive buffering for reduced latency
    - Parallel STT and AI processing pipelines
    - Adaptive streaming based on network conditions
    - Preemptive TTS generation for common responses
    - Real-time audio preprocessing optimization
    - Intelligent resource allocation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = get_logger(f"{__name__}.AudioStreamOptimizer")

        # Stream buffers for active sessions
        self.stream_buffers: Dict[str, StreamBuffer] = {}

        # Processing pipelines
        self.pipelines: Dict[str, ProcessingPipeline] = {}

        # Predictive caching
        self.predictive_cache = PredictiveCache()

        # Performance tracking
        self.processing_stats: Dict[str, Dict[str, Any]] = {}

        # Optimization settings
        self.enable_predictive_buffering = True
        self.enable_parallel_processing = True
        self.enable_preemptive_tts = True
        self.adaptive_buffering_enabled = True

        # Initialize pipelines
        self._initialize_pipelines()

    def _initialize_pipelines(self) -> None:
        """Initialize processing pipelines."""
        # STT processing pipeline
        self.pipelines["stt"] = ProcessingPipeline(
            pipeline_id="stt_processing",
            stages=[
                self._preprocess_audio,
                self._extract_audio_features,
                self._optimize_for_stt,
            ],
            timeout=10.0,
            max_concurrent=5,
        )

        # TTS processing pipeline
        self.pipelines["tts"] = ProcessingPipeline(
            pipeline_id="tts_processing",
            stages=[
                self._optimize_tts_input,
                self._select_optimal_voice,
                self._generate_with_prediction,
            ],
            timeout=15.0,
            max_concurrent=3,
        )

        # Parallel STT + AI pipeline
        self.pipelines["parallel_stt_ai"] = ProcessingPipeline(
            pipeline_id="parallel_stt_ai",
            stages=[
                self._parallel_stt_processing,
                self._parallel_ai_processing,
                self._merge_results,
            ],
            timeout=25.0,
            max_concurrent=2,
        )

    async def optimize_stream(
        self, stream_id: str, audio_data: bytes, session_context: Dict[str, Any] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Optimize audio stream for real-time processing.

        Args:
            stream_id: Unique stream identifier
            audio_data: Incoming audio data
            session_context: Session context information

        Returns:
            Tuple of (optimized_audio, optimization_metadata)
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="stream_optimization", stream_id=stream_id
            ) as trace_id:
                # Get or create stream buffer
                buffer = self._get_or_create_buffer(stream_id)

                # Add data to buffer
                buffer.add_data(audio_data)

                # Adaptive buffering
                if self.adaptive_buffering_enabled:
                    await self._adapt_buffer_size(buffer, session_context)

                # Check if we have enough data for processing
                if buffer.size >= buffer.optimal_size:
                    # Extract optimal chunk
                    chunk_data = buffer.get_data(buffer.optimal_size)

                    if chunk_data:
                        # Apply streaming optimizations
                        (
                            optimized_data,
                            metadata,
                        ) = await self._apply_streaming_optimizations(
                            chunk_data, session_context
                        )

                        # Update performance stats
                        processing_time = time.time() - start_time
                        self._update_stream_stats(stream_id, processing_time, metadata)

                        self.logger.debug(
                            "stream_optimized",
                            stream_id=stream_id,
                            original_size=len(audio_data),
                            optimized_size=len(optimized_data),
                            processing_time=processing_time,
                            trace_id=trace_id,
                        )

                        return optimized_data, metadata

                # Return original data if not enough for optimization
                return audio_data, {"status": "insufficient_data"}

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(
                "stream_optimization_failed",
                stream_id=stream_id,
                processing_time=processing_time,
                error=str(e),
            )
            return audio_data, {"error": str(e)}

    async def process_parallel_pipelines(
        self,
        stream_id: str,
        audio_data: bytes,
        text_data: str = None,
        session_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Process audio through parallel pipelines for reduced latency.

        Args:
            stream_id: Stream identifier
            audio_data: Audio data for STT pipeline
            text_data: Text data for AI pipeline
            session_context: Session context

        Returns:
            Combined results from parallel processing
        """
        start_time = time.time()

        try:
            # Start parallel processing tasks
            tasks = []

            if audio_data and self.enable_parallel_processing:
                # STT processing task
                stt_task = asyncio.create_task(
                    self.pipelines["stt"].execute(audio_data, session_context)
                )
                tasks.append(("stt", stt_task))

            if text_data:
                # AI processing task (placeholder)
                ai_task = asyncio.create_task(
                    self._process_ai_text(text_data, session_context)
                )
                tasks.append(("ai", ai_task))

            # Wait for all tasks with timeout
            results = {}
            pending_tasks = dict(tasks)

            try:
                # Wait for first completion or timeout
                done, pending = await asyncio.wait(
                    [task for _, task in tasks],
                    timeout=20.0,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Process completed tasks
                for task in done:
                    for name, task_obj in pending_tasks.items():
                        if task_obj == task:
                            try:
                                results[name] = await task
                                del pending_tasks[name]
                            except Exception as e:
                                results[name] = {"error": str(e)}
                            break

                # Cancel remaining tasks
                for task in pending:
                    task.cancel()

            except asyncio.TimeoutError:
                # Cancel all tasks on timeout
                for task in pending_tasks.values():
                    task.cancel()
                results["timeout"] = True

            # Calculate total processing time
            processing_time = time.time() - start_time

            # Update performance metrics
            await voice_performance_monitor.update_latency_stage(
                stream_id, "parallel_processing_complete"
            )

            self.logger.info(
                "parallel_processing_complete",
                stream_id=stream_id,
                processing_time=processing_time,
                completed_tasks=len(results),
                timeout="timeout" in results,
            )

            return {
                "results": results,
                "processing_time": processing_time,
                "parallel_efficiency": self._calculate_parallel_efficiency(results),
            }

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(
                "parallel_processing_failed",
                stream_id=stream_id,
                processing_time=processing_time,
                error=str(e),
            )
            return {"error": str(e), "processing_time": processing_time}

    async def generate_preemptive_tts(
        self, common_responses: List[str], session_context: Dict[str, Any] = None
    ) -> Dict[str, SpeechSynthesisResult]:
        """
        Generate TTS for common responses preemptively.

        Args:
            common_responses: List of common response texts
            session_context: Session context

        Returns:
            Dictionary of text to TTS results
        """
        if not self.enable_preemptive_tts:
            return {}

        start_time = time.time()

        try:
            # Check cache first
            cached_results = {}
            uncached_responses = []

            for response in common_responses:
                cache_key = f"preemptive_tts_{hash(response)}"
                cached = self.predictive_cache.get_prediction(cache_key)
                if cached:
                    cached_results[response] = cached
                else:
                    uncached_responses.append(response)

            # Generate TTS for uncached responses
            if uncached_responses:
                tasks = []
                for response in uncached_responses[:5]:  # Limit concurrent generation
                    task = asyncio.create_task(
                        self._generate_single_preemptive_tts(response, session_context)
                    )
                    tasks.append((response, task))

                # Wait for completions with timeout
                for response, task in tasks:
                    try:
                        result = await asyncio.wait_for(task, timeout=15.0)
                        if result:
                            cached_results[response] = result
                            # Cache the result
                            cache_key = f"preemptive_tts_{hash(response)}"
                            self.predictive_cache.add_prediction(cache_key, result)
                    except asyncio.TimeoutError:
                        self.logger.warning(
                            "preemptive_tts_timeout", response=response[:50]
                        )
                    except Exception as e:
                        self.logger.error(
                            "preemptive_tts_error", response=response[:50], error=str(e)
                        )

            processing_time = time.time() - start_time
            self.logger.info(
                "preemptive_tts_generation_complete",
                requested_responses=len(common_responses),
                cached_results=len(cached_results) - len(uncached_responses),
                generated_results=len(uncached_responses),
                processing_time=processing_time,
            )

            return cached_results

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(
                "preemptive_tts_generation_failed",
                processing_time=processing_time,
                error=str(e),
            )
            return {}

    async def _adapt_buffer_size(
        self, buffer: StreamBuffer, context: Dict[str, Any]
    ) -> None:
        """Adapt buffer size based on network conditions and processing load."""
        try:
            # Analyze recent performance
            recent_stats = self.processing_stats.get(buffer.stream_id, {})
            avg_processing_time = recent_stats.get("avg_processing_time", 0.1)

            # Network latency estimation (simplified)
            network_latency = context.get("network_latency", 0.05)

            # Adjust buffer size based on processing and network conditions
            if avg_processing_time > 0.5 or network_latency > 0.2:
                # High latency - increase buffer size
                new_size = min(buffer.max_size, buffer.optimal_size + 1024)
                buffer.optimal_size = new_size
            elif avg_processing_time < 0.1 and network_latency < 0.05:
                # Low latency - can reduce buffer size
                new_size = max(buffer.min_size, buffer.optimal_size - 512)
                buffer.optimal_size = new_size

        except Exception as e:
            self.logger.warning("buffer_adaptation_failed", error=str(e))

    async def _apply_streaming_optimizations(
        self, audio_data: bytes, context: Dict[str, Any]
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Apply streaming-specific optimizations."""
        try:
            # Remove silence at beginning and end
            optimized_data = await self._remove_silence(audio_data)

            # Apply audio normalization
            optimized_data = await self._normalize_audio_level(optimized_data)

            # Apply predictive filtering based on context
            if context and context.get("voice_activity_detected", True):
                optimized_data = await self._apply_voice_enhancement(optimized_data)

            metadata = {
                "original_size": len(audio_data),
                "optimized_size": len(optimized_data),
                "optimizations_applied": ["silence_removal", "normalization"],
                "quality_improvement": self._estimate_quality_improvement(
                    audio_data, optimized_data
                ),
            }

            return optimized_data, metadata

        except Exception as e:
            self.logger.error("streaming_optimization_failed", error=str(e))
            return audio_data, {"error": str(e)}

    async def _remove_silence(self, audio_data: bytes) -> bytes:
        """Remove silence from audio data."""
        # Simplified silence removal
        try:
            # Convert to 16-bit samples
            import numpy as np

            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Calculate energy
            energy = np.abs(audio_array.astype(np.float32))

            # Find non-silent regions (simple threshold-based)
            threshold = np.max(energy) * 0.05  # 5% of max energy
            non_silent = energy > threshold

            if np.any(non_silent):
                # Find first and last non-silent samples
                first_sample = np.argmax(non_silent)
                last_sample = len(non_silent) - np.argmax(non_silent[::-1]) - 1

                # Add small padding
                padding = min(1000, len(audio_array) // 20)
                first_sample = max(0, first_sample - padding)
                last_sample = min(len(audio_array), last_sample + padding)

                # Extract non-silent region
                trimmed_audio = audio_array[first_sample:last_sample]
                return trimmed_audio.tobytes()

            return audio_data

        except Exception as e:
            self.logger.warning("silence_removal_failed", error=str(e))
            return audio_data

    async def _normalize_audio_level(self, audio_data: bytes) -> bytes:
        """Normalize audio to optimal level."""
        try:
            import numpy as np

            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)

            # Calculate RMS level
            rms = np.sqrt(np.mean(audio_array**2))

            # Target RMS level (about 50% of max for 16-bit)
            target_rms = 16384 * 0.5  # 50% of 16-bit range

            if rms > 0:
                # Calculate gain
                gain = target_rms / rms
                gain = min(gain, 4.0)  # Limit maximum gain

                # Apply gain
                normalized_audio = audio_array * gain

                # Clip to prevent overflow
                normalized_audio = np.clip(normalized_audio, -32768, 32767)

                return normalized_audio.astype(np.int16).tobytes()

            return audio_data

        except Exception as e:
            self.logger.warning("audio_normalization_failed", error=str(e))
            return audio_data

    async def _apply_voice_enhancement(self, audio_data: bytes) -> bytes:
        """Apply voice-specific enhancements."""
        # Placeholder for voice enhancement
        # In a real implementation, this would apply:
        # - Voice frequency range optimization
        # - Breath noise reduction
        # - De-essing
        # - Dynamic equalization
        return audio_data

    def _estimate_quality_improvement(self, original: bytes, optimized: bytes) -> float:
        """Estimate quality improvement (simplified)."""
        try:
            # Simple size-based estimation
            size_reduction = len(original) - len(optimized)
            return min(100.0, (size_reduction / len(original)) * 100.0)
        except:
            return 0.0

    async def _generate_single_preemptive_tts(
        self, text: str, context: Dict[str, Any]
    ) -> Optional[SpeechSynthesisResult]:
        """Generate TTS for a single response."""
        try:
            request = TextToSpeechRequest(
                text=text,
                voice=context.get("preferred_voice", "default"),
                language=context.get("language", "en-US"),
                speed=1.0,
            )

            result = await tts_service.synthesize_speech(
                request, correlation_id=context.get("correlation_id")
            )

            return result

        except Exception as e:
            self.logger.error("single_preemptive_tts_failed", error=str(e))
            return None

    async def _process_ai_text(
        self, text: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process text through AI pipeline (placeholder)."""
        # In a real implementation, this would call the AI/DM service
        await asyncio.sleep(0.1)  # Simulate processing time
        return {"ai_response": f"Processed: {text[:50]}...", "confidence": 0.9}

    def _get_or_create_buffer(self, stream_id: str) -> StreamBuffer:
        """Get or create stream buffer."""
        if stream_id not in self.stream_buffers:
            self.stream_buffers[stream_id] = StreamBuffer(stream_id=stream_id)
            self.logger.info("created_stream_buffer", stream_id=stream_id)
        return self.stream_buffers[stream_id]

    def _update_stream_stats(
        self, stream_id: str, processing_time: float, metadata: Dict[str, Any]
    ) -> None:
        """Update stream processing statistics."""
        if stream_id not in self.processing_stats:
            self.processing_stats[stream_id] = {
                "total_processing_time": 0.0,
                "processing_count": 0,
                "avg_processing_time": 0.0,
                "optimizations_applied": [],
            }

        stats = self.processing_stats[stream_id]
        stats["total_processing_time"] += processing_time
        stats["processing_count"] += 1
        stats["avg_processing_time"] = (
            stats["total_processing_time"] / stats["processing_count"]
        )
        stats["last_processing_time"] = processing_time
        stats["last_metadata"] = metadata

    def _calculate_parallel_efficiency(self, results: Dict[str, Any]) -> float:
        """Calculate parallel processing efficiency."""
        try:
            if not results:
                return 0.0

            # Simple efficiency calculation based on completed tasks
            completed_tasks = len(
                [
                    r
                    for r in results.values()
                    if not isinstance(r, dict) or "error" not in r
                ]
            )
            total_tasks = len(results)

            return (completed_tasks / total_tasks) * 100.0

        except Exception:
            return 0.0

    # Pipeline stage implementations
    async def _preprocess_audio(self, data: bytes, context: Dict[str, Any]) -> bytes:
        """Audio preprocessing stage."""
        return await self._remove_silence(data)

    async def _extract_audio_features(
        self, data: bytes, context: Dict[str, Any]
    ) -> bytes:
        """Audio feature extraction stage."""
        return data  # Placeholder

    async def _optimize_for_stt(self, data: bytes, context: Dict[str, Any]) -> bytes:
        """STT optimization stage."""
        return data  # Placeholder

    async def _optimize_tts_input(self, data: Any, context: Dict[str, Any]) -> Any:
        """TTS input optimization stage."""
        return data  # Placeholder

    async def _select_optimal_voice(self, data: Any, context: Dict[str, Any]) -> Any:
        """Voice selection stage."""
        return data  # Placeholder

    async def _generate_with_prediction(
        self, data: Any, context: Dict[str, Any]
    ) -> Any:
        """Predictive generation stage."""
        return data  # Placeholder

    async def _parallel_stt_processing(
        self, data: bytes, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parallel STT processing."""
        return {"stt_result": "processed", "confidence": 0.9}

    async def _parallel_ai_processing(
        self, data: bytes, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parallel AI processing."""
        return {"ai_result": "generated", "quality": 0.8}

    async def _merge_results(
        self, data: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge parallel processing results."""
        return {"merged_results": data, "efficiency": 0.9}

    def get_stream_info(self, stream_id: str) -> Optional[AudioStreamInfo]:
        """Get stream information."""
        if stream_id in self.stream_buffers:
            buffer = self.stream_buffers[stream_id]
            return AudioStreamInfo(
                stream_id=stream_id,
                user_id="optimized_stream",
                channel_id="optimized_channel",
                session_id=stream_id,
                format="optimized",
                sample_rate=16000,
                channels=1,
                started_at=datetime.utcnow(),
                last_activity=buffer._last_access,
                is_active=True,
                buffer_size=buffer.size,
            )
        return None

    def cleanup_stream(self, stream_id: str) -> None:
        """Clean up stream resources."""
        if stream_id in self.stream_buffers:
            del self.stream_buffers[stream_id]
        if stream_id in self.processing_stats:
            del self.processing_stats[stream_id]
        self.logger.info("cleaned_up_optimized_stream", stream_id=stream_id)

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the stream optimizer."""
        active_streams = len(self.stream_buffers)
        total_buffer_size = sum(buffer.size for buffer in self.stream_buffers.values())

        # Calculate average processing time
        avg_processing_time = 0.0
        if self.processing_stats:
            total_time = sum(
                stats.get("total_processing_time", 0)
                for stats in self.processing_stats.values()
            )
            total_count = sum(
                stats.get("processing_count", 0)
                for stats in self.processing_stats.values()
            )
            if total_count > 0:
                avg_processing_time = total_time / total_count

        return {
            "status": "healthy" if active_streams >= 0 else "error",
            "active_streams": active_streams,
            "total_buffer_size_mb": total_buffer_size / (1024 * 1024),
            "average_processing_time": avg_processing_time,
            "predictive_cache_entries": len(self.predictive_cache._cache),
            "parallel_processing_enabled": self.enable_parallel_processing,
            "preemptive_tts_enabled": self.enable_preemptive_tts,
            "adaptive_buffering_enabled": self.adaptive_buffering_enabled,
        }


# Global audio stream optimizer instance
audio_stream_optimizer = AudioStreamOptimizer()
