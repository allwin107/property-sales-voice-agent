"""
TTS Service - Cartesia Integration with Advanced Interruption Handling
Handles Text-to-Speech conversion with word-level timestamp tracking and interruption support
"""
import logging
import asyncio
import time
import uuid
from cartesia import AsyncCartesia
from services.tts_base import BaseTTSService

logger = logging.getLogger(__name__)


class CartesiaTTSService(BaseTTSService):
    """
    Enhanced TTS service with interruption handling and spoken text tracking for hospital calls
    """
    
    def __init__(self, api_key: str, voice_id: str, model_id: str = "sonic-english", speed: str = "normal"):
        """
        Initialize Cartesia TTS service
        
        Args:
            api_key: Cartesia API key
            voice_id: Voice ID to use for synthesis
            model_id: Model ID (default: "sonic-english")
            speed: Speaking speed - can be "slowest", "slow", "normal", "fast", "fastest"
                   or float between -1.0 to 1.0
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.speed = speed
        self.client = AsyncCartesia(api_key=api_key)
        self.ws = None
        
        # Audio output format for Twilio (mulaw, 8kHz)
        self.output_format = {
            "container": "raw",
            "encoding": "pcm_mulaw",
            "sample_rate": 8000
        }
        
        # Context and cancellation management
        self.active_contexts = set()
        self.cancelled_contexts = set()
        self.context_lock = asyncio.Lock()
        self.cancellation_event = asyncio.Event()
        self.tts_in_progress = False
        self.current_task = None
        self.current_send_audio_callback = None
        
        # Enhanced timestamp tracking for interruption handling
        self.current_text = None
        self.current_words = []  # List of words in order
        self.word_timings = {}  # word_index -> (start_time, end_time)
        self.playback_start_time = None
        self.last_spoken_text = ""
        self.audio_chunks_sent = 0
        self.estimated_duration_per_chunk = 0.032  # 32ms per chunk estimate
        
        # Fallback timing estimation when timestamps unavailable
        self.chars_per_second = 12  # Average speaking rate
        self.processing_delay = 0.2  # Account for processing delays
        
        logger.info("[TTS] CartesiaTTSService instance created")
    
    async def initialize(self) -> bool:
        """
        Initialize TTS service and establish WebSocket connection.
        
        Returns:
            True if initialization successful, False otherwise
        """
        start_time = time.time()
        try:
            self.ws = await self.client.tts.websocket()
            elapsed = time.time() - start_time
            logger.info(f"[TIMING] Cartesia TTS initialized in {elapsed:.3f}s")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Cartesia TTS initialization failed: {e}", exc_info=True)
            return False
    
    def set_speed(self, speed):
        """
        Set the default speaking speed for synthesis.
        
        Args:
            speed: Can be one of:
                   - String: "slowest", "slow", "normal", "fast", "fastest"
                   - Float: -1.0 to 1.0 (-1.0 = slowest, 0 = normal, 1.0 = fastest)
        """
        self.speed = speed
        logger.info(f"[TTS] Speed set to: {speed}")
    
    def get_speed(self) -> str:
        """Get the current default speed setting."""
        return self.speed
    
    def estimate_spoken_text_by_duration(self, elapsed_time: float) -> str:
        """
        Estimate spoken text based on duration when timestamps aren't available.
        
        Args:
            elapsed_time: Time elapsed since playback started
            
        Returns:
            Estimated spoken text
        """
        if not self.current_text:
            return ""
        
        # Adjust for processing delays
        adjusted_time = max(0, elapsed_time - self.processing_delay)
        
        # Estimate characters spoken based on time
        chars_spoken = int(adjusted_time * self.chars_per_second)
        
        if chars_spoken >= len(self.current_text):
            return self.current_text
        elif chars_spoken <= 0:
            return ""
        else:
            # Find word boundary near the estimated position
            text_portion = self.current_text[:chars_spoken]
            # Find last complete word
            last_space = text_portion.rfind(' ')
            if last_space > 0:
                return text_portion[:last_space]
            else:
                return text_portion
    
    def get_spoken_text_at_time(self, elapsed_time: float) -> str:
        """
        Calculate which part of the text was spoken at given time.
        
        Args:
            elapsed_time: Time elapsed since playback started
            
        Returns:
            Text that was spoken up to this point
        """
        if not self.current_text:
            logger.warning("[TTS] No current text available for spoken text calculation")
            return ""
        
        # First try timestamp-based calculation (most accurate)
        if self.current_words and self.word_timings:
            try:
                # Adjust for processing delays
                adjusted_time = elapsed_time + 0.1  # Small buffer for processing
                
                spoken_words = []
                for i, word in enumerate(self.current_words):
                    if i in self.word_timings:
                        start_time, end_time = self.word_timings[i]
                        # Convert from milliseconds to seconds if needed
                        end_time_seconds = end_time / 1000.0 if end_time > 100 else end_time
                        
                        if end_time_seconds <= adjusted_time:
                            spoken_words.append(word)
                        else:
                            break
                    else:
                        # If timing not available for this word, stop
                        break
                
                if spoken_words:
                    spoken_text = " ".join(spoken_words)
                    logger.debug(f"[TTS] Timestamp-based spoken text: '{spoken_text}'")
                    return spoken_text
            except Exception as e:
                logger.warning(f"[TTS] Error in timestamp calculation: {e}")
        
        # Fallback to duration-based estimation
        estimated_text = self.estimate_spoken_text_by_duration(elapsed_time)
        logger.debug(f"[TTS] Duration-based estimated text: '{estimated_text}'")
        return estimated_text
    
    async def get_last_spoken_text(self) -> str:
        """
        Get the last spoken text portion (called when interrupted).
        
        Returns:
            Last spoken text before interruption
        """
        return self.last_spoken_text
    
    def reset_tracking(self):
        """Reset all tracking variables for new synthesis."""
        self.current_text = None
        self.current_words = []
        self.word_timings = {}
        self.playback_start_time = None
        self.last_spoken_text = ""
        self.audio_chunks_sent = 0
    
    async def synthesize(self, text: str, send_audio_callback, speed=None) -> bool:
        """
        Synthesize text to speech and send audio chunks via callback.
        
        Args:
            text: Text to synthesize
            send_audio_callback: Async callback function for audio chunks
            speed: Optional speed override. If None, uses instance default.
            
        Returns:
            True if synthesis completed successfully
        """
        self.current_send_audio_callback = send_audio_callback
        
        # Always cancel any existing synthesis first
        await self.stop()
        await asyncio.sleep(0.01)
        
        async with self.context_lock:
            if self.cancellation_event.is_set():
                logger.info("[TTS] Cancelled before starting")
                return False
            
            # Generate unique context ID for this synthesis
            context_id = str(uuid.uuid4())
            synthesis_start = time.time()
            logger.info(f"[TTS] Starting synthesis for context {context_id}")
            logger.info(f"[TTS] Text: '{text[:100]}...' ({len(text)} chars)")
            
            # Add to active contexts and initialize tracking
            self.active_contexts.add(context_id)
            self.tts_in_progress = True
            self.reset_tracking()
            self.current_text = text
            
            # Pre-split text into words for tracking
            self.current_words = text.split()
            
            chunk_size = 256  # Small chunks for fast interruption response
            
            try:
                # Determine speed to use (parameter override or instance default)
                synthesis_speed = speed if speed is not None else self.speed
                
                # Create voice configuration
                voice_config = {
                    "mode": "id",
                    "id": self.voice_id
                }
                
                # Add experimental speed controls if not normal
                if synthesis_speed != "normal" and synthesis_speed != 0:
                    voice_config["__experimental_controls"] = {
                        "speed": synthesis_speed
                    }
                    logger.info(f"[TTS] Using speed: {synthesis_speed}")
                
                # Create synthesis parameters
                synthesis_params = {
                    "model_id": self.model_id,
                    "transcript": text,
                    "voice": voice_config,
                    "language": "en",  # English language
                    "context_id": context_id,
                    "output_format": self.output_format,
                    "add_timestamps": True,  # Enable word-level timestamps
                    "stream": True
                }
                
                logger.debug(f"[TTS] Synthesis params: {synthesis_params}")
                
                # Create and run synthesis task
                self.current_task = asyncio.create_task(
                    self._process_synthesis(
                        synthesis_params, 
                        send_audio_callback, 
                        context_id, 
                        chunk_size
                    )
                )
                
                # Wait for the task to complete
                await self.current_task
                
            except asyncio.CancelledError:
                logger.info(f"[TTS] Synthesis cancelled for context {context_id}")
                if self.current_send_audio_callback:
                    await self.current_send_audio_callback(None, "clearAudio")
                return False
            except Exception as e:
                logger.error(f"[ERROR] Error in synthesis for context {context_id}: {e}", exc_info=True)
                return False
            finally:
                # Cleanup
                self.active_contexts.discard(context_id)
                self.cancelled_contexts.discard(context_id)
                self.tts_in_progress = False
                self.current_task = None
                
                # Calculate and store spoken text for later retrieval
                if self.playback_start_time:
                    total_playback_time = time.time() - self.playback_start_time
                    spoken_text = self.get_spoken_text_at_time(total_playback_time)
                    self.last_spoken_text = spoken_text
                    
                    logger.info(f"[TTS] Playback duration: {total_playback_time:.3f}s")
                    logger.info(f"[TTS] Spoken text stored: '{spoken_text[:100]}...' ({len(spoken_text)} chars)")
                
                total_time = time.time() - synthesis_start
                logger.info(f"[TIMING] TTS synthesis completed in {total_time:.3f}s")
                return True
    
    async def _process_synthesis(
        self, 
        synthesis_params: dict, 
        send_audio_callback, 
        context_id: str, 
        chunk_size: int
    ):
        """
        Process the synthesis using Cartesia WebSocket API.
        
        Args:
            synthesis_params: Synthesis configuration
            send_audio_callback: Callback for audio chunks
            context_id: Unique context identifier
            chunk_size: Size of audio chunks to send
        """
        send_start = time.time()
        
        try:
            # Send synthesis request and get response iterator
            response_iterator = await self.ws.send(**synthesis_params)
            
            send_time = time.time() - send_start
            logger.info(f"[TIMING] TTS send completed in {send_time:.3f}s")
            
            # Track when playback starts
            first_audio_chunk = True
            
            # Process the streaming response
            async for output in response_iterator:
                # Check for cancellation
                if self.cancellation_event.is_set() or context_id in self.cancelled_contexts:
                    logger.info(f"[TTS] Cancellation detected for context {context_id}")
                    await send_audio_callback(None, "clearAudio")
                    break
                
                # Handle word timestamps if available
                if hasattr(output, 'word_timestamps') and output.word_timestamps:
                    try:
                        timestamps = output.word_timestamps
                        words = timestamps.words if hasattr(timestamps, 'words') else []
                        starts = timestamps.start if hasattr(timestamps, 'start') else []
                        ends = timestamps.end if hasattr(timestamps, 'end') else []
                        
                        if words and starts and ends and len(words) == len(starts) == len(ends):
                            # Store word timings by index
                            base_index = len(self.word_timings)
                            for i, (word, start, end) in enumerate(zip(words, starts, ends)):
                                word_index = base_index + i
                                self.word_timings[word_index] = (start, end)
                            
                            logger.info(f"[TTS] Stored timings for {len(words)} words (total: {len(self.word_timings)})")
                            
                            # Log a few recent timings for debugging
                            for word, start, end in zip(words[-2:], starts[-2:], ends[-2:]):
                                logger.debug(f"[TTS] Word: '{word}' [{start:.2f}s - {end:.2f}s]")
                        else:
                            logger.warning(
                                f"[TTS] Timestamp data mismatch: "
                                f"words={len(words)}, starts={len(starts)}, ends={len(ends)}"
                            )
                    except Exception as e:
                        logger.error(f"[ERROR] Error processing timestamps: {e}")
                
                # Handle audio data
                if hasattr(output, 'audio') and output.audio:
                    # Mark playback start time on first audio chunk
                    if first_audio_chunk:
                        self.playback_start_time = time.time()
                        first_audio_chunk = False
                        logger.info(f"[TTS] Playback started for: '{self.current_text[:50]}...'")
                    
                    audio_data = output.audio
                    
                    # Process in small chunks for fast interruption response
                    for i in range(0, len(audio_data), chunk_size):
                        # Check cancellation before each chunk
                        if self.cancellation_event.is_set() or context_id in self.cancelled_contexts:
                            logger.info("[TTS] Cancellation during chunk processing")
                            await send_audio_callback(None, "clearAudio")
                            return
                        
                        chunk = audio_data[i:i + chunk_size]
                        try:
                            await send_audio_callback(chunk, "playAudio")
                            self.audio_chunks_sent += 1
                        except Exception as e:
                            logger.error(f"[ERROR] Chunk send error: {e}")
                            return
        
        except asyncio.CancelledError:
            logger.info(f"[TTS] Context {context_id} processing cancelled")
            await send_audio_callback(None, "clearAudio")
        except Exception as e:
            logger.error(f"[ERROR] Error processing synthesis for context {context_id}: {e}", exc_info=True)
    
    async def stop(self):
        """Stop ongoing TTS synthesis immediately and calculate spoken text."""
        stop_start = time.time()
        logger.info("[TTS] Stopping TTS synthesis")
        
        # Calculate spoken text BEFORE stopping (if currently playing)
        if self.tts_in_progress and self.playback_start_time and self.current_text:
            elapsed_time = time.time() - self.playback_start_time
            spoken_text = self.get_spoken_text_at_time(elapsed_time)
            self.last_spoken_text = spoken_text
            
            logger.info(f"[TTS] Interrupted after {elapsed_time:.3f}s")
            logger.info(f"[TTS] Spoken portion: '{spoken_text[:100]}...' ({len(spoken_text)} chars)")
        
        # Set cancellation event
        self.cancellation_event.set()
        
        # Send clearAudio immediately
        if self.current_send_audio_callback:
            try:
                await self.current_send_audio_callback(None, "clearAudio")
            except Exception as e:
                logger.error(f"[ERROR] Error in clearAudio during stop: {e}")
        
        # Cancel current task
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self.current_task), timeout=0.05)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        # Add all active contexts to cancelled set
        self.cancelled_contexts.update(self.active_contexts)
        
        # Reset state
        self.tts_in_progress = False
        
        # Brief wait for cleanup
        await asyncio.sleep(0.01)
        
        # Reset cancellation event
        self.cancellation_event.clear()
        
        stop_time = time.time() - stop_start
        logger.info(f"[TIMING] TTS stop completed in {stop_time:.3f}s")
    
    async def close(self):
        """Close TTS service and cleanup all resources."""
        close_start = time.time()
        logger.info("[CLEANUP] Closing TTS service")
        
        # Stop any ongoing synthesis
        await self.stop()
        
        # Close WebSocket connection
        if self.ws:
            try:
                await self.ws.close()
                logger.info("[CONNECTION] TTS WebSocket closed")
            except Exception as e:
                logger.error(f"[ERROR] Error closing WebSocket: {e}")
        
        # Close Cartesia client
        if self.client:
            try:
                await self.client.close()
                logger.info("[CONNECTION] Cartesia client closed")
            except Exception as e:
                logger.error(f"[ERROR] Error closing client: {e}")
        
        close_time = time.time() - close_start
        logger.info(f"[TIMING] TTS service closed in {close_time:.3f}s")


# Convenience function for quick initialization
async def create_tts_service(
    api_key: str, 
    voice_id: str, 
    model_id: str = "sonic-english",
    speed: str = "normal"
) -> CartesiaTTSService:
    """
    Create and initialize a Cartesia TTS service instance.
    
    Args:
        api_key: Cartesia API key
        voice_id: Voice ID to use
        model_id: Model ID (default: "sonic-english")
        speed: Speaking speed (default: "normal")
        
    Returns:
        Initialized CartesiaTTSService instance
    """
    service = CartesiaTTSService(
        api_key=api_key, 
        voice_id=voice_id, 
        model_id=model_id,
        speed=speed
    )
    await service.initialize()
    
    logger.info("[FACTORY] Created and initialized TTS service")
    return service


# Compatibility alias
TTSService = CartesiaTTSService
