"""
STT Service - Deepgram Integration with Real-time Transcription
Handles Speech-to-Text conversion with async event handling and interruption detection
"""
import logging
import asyncio
import time
from deepgram import (
    DeepgramClient, 
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions
)
from services.stt_base import BaseSTTService
import config

logger = logging.getLogger(__name__)


class DeepgramSTTService(BaseSTTService):
    """
    Enhanced STT service with real-time streaming transcription for hospital calls
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Deepgram STT service
        
        Args:
            api_key: Deepgram API key
        """
        self.api_key = api_key
        self.callback_function = None
        self.is_finals = []
        self.processing_lock = asyncio.Lock()
        self.once = 0
        self.dg_connection = None
        self._is_connected = False  # Changed to private attribute
        self.deepgram_client = None
        self.session_start_time = None
        
        logger.info("[STT] DeepgramSTTService instance created")
    
    @property
    def is_connected(self) -> bool:
        """Check if the STT service is currently connected and ready."""
        return self._is_connected
    
    async def initialize(self, api_key: str, callback=None, encoding: str = "mulaw"):
        """
        Initialize STT service with callback function for transcription events.
        
        Args:
            api_key: Deepgram API key (can override instance key)
            callback: Async callback function to handle transcribed text
            encoding: Audio encoding format ('mulaw' or 'linear16')
            
        Returns:
            True if initialization successful, False otherwise
        """
        init_start = time.time()
        try:
            logger.info(f"[STT] Initializing Deepgram STT service with encoding: {encoding}, language: {config.STT_LANGUAGE}")
            
            # Store the callback function
            if callback:
                self.callback_function = callback
            
            # Create Deepgram client with API key and keepalive config
            dg_config = DeepgramClientOptions(
                options={"keepalive": "true"}
            )
            self.deepgram_client = DeepgramClient(self.api_key or api_key, dg_config)
            
            # Create WebSocket connection
            self.dg_connection = self.deepgram_client.listen.asyncwebsocket.v("1")
            logger.info("[STT] Deepgram connection created")
            
            # Store reference to self for closures
            service_instance = self
            
            # ... (event handlers implementation omitted for brevity in replace call) ...
            # Note: I'm keeping the implementation of handlers since I'm replacing the whole block
            
            # Define event handlers with proper signatures for Deepgram SDK
            async def on_message(self_dg, result, **kwargs):
                """Handle transcription messages from Deepgram."""
                try:
                    if not hasattr(result, 'channel') or not result.channel.alternatives:
                        return
                    
                    sentence = result.channel.alternatives[0].transcript
                    if len(sentence) == 0:
                        return
                    
                    if not result.is_final and len(sentence.strip()) > 0:
                        service_instance.once += 1
                        if service_instance.callback_function and (service_instance.once <= 1):
                            await service_instance.callback_function("__FORCE_STOP__")
                        return
                        
                    if result.is_final:
                        async with service_instance.processing_lock:
                            service_instance.is_finals.append(sentence)
                            if hasattr(result, 'speech_final') and result.speech_final and service_instance.is_finals:
                                utterance = " ".join(service_instance.is_finals)
                                if service_instance.callback_function:
                                    await service_instance.callback_function(utterance)
                                service_instance.once = 0
                                service_instance.is_finals.clear()
                except Exception as e:
                    logger.error(f"[ERROR] Error in on_message: {e}")

            async def on_utterance_end(self_dg, utterance_end=None, **kwargs):
                async with service_instance.processing_lock:
                    if service_instance.is_finals:
                        utterance = " ".join(service_instance.is_finals)
                        if service_instance.callback_function:
                            await service_instance.callback_function(utterance)
                        service_instance.once = 0
                        service_instance.is_finals.clear()

            async def on_open(self_dg, open_event=None, **kwargs):
                service_instance._is_connected = True
            
            async def on_error(self_dg, error=None, **kwargs):
                logger.error(f"[ERROR] Deepgram error: {error}")
            
            async def on_close(self_dg, close_event=None, **kwargs):
                service_instance._is_connected = False
            
            # Register handlers
            self.dg_connection.on(LiveTranscriptionEvents.Open, on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.dg_connection.on(LiveTranscriptionEvents.Close, on_close)
            self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
            
            # Configure options
            options = LiveOptions(
                model=config.DEEPGRAM_MODEL,
                language=config.STT_LANGUAGE,  # Dynamic language
                smart_format=True,
                encoding=encoding,
                channels=1,
                sample_rate=config.DEEPGRAM_SAMPLE_RATE,
                interim_results=True,
                utterance_end_ms=1000,  # Minimum required by Deepgram API
                vad_events=True,
                endpointing=config.DEEPGRAM_ENDPOINTING
            )
            
            # Performance optimization addons
            addons = {
                "no_delay": "true"  # Minimize latency for real-time feel
            }
            
            # Start the WebSocket connection
            result = await self.dg_connection.start(options, addons=addons)
            if result is False:
                logger.error("[ERROR] Failed to connect to Deepgram")
                return False
            
            # Small delay to ensure WebSocket is fully connected before audio starts
            await asyncio.sleep(0.1)
            
            logger.info("[CONNECTION] Deepgram connected successfully")
            self._is_connected = True
            logger.info(f"[DEBUG] _is_connected set to: {self._is_connected}")
            self.session_start_time = time.time()
            
            init_time = time.time() - init_start
            logger.info(f"[TIMING] Deepgram STT initialization took {init_time:.3f}s")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Deepgram STT: {e}", exc_info=True)
            self._is_connected = False
            return False
    
    async def process_audio(self, audio_chunk: bytes) -> bool:
        """
        Process audio chunk by sending to Deepgram for transcription.
        
        Args:
            audio_chunk: Raw audio bytes (mulaw encoded, 8kHz)
            
        Returns:
            True if audio was sent successfully, False otherwise
        """
        if not self._is_connected:
            # Only log first warning to avoid spam
            if not hasattr(self, '_warned_not_connected'):
                logger.warning(f"[WARNING] Attempting to process audio while not connected (_is_connected={self._is_connected})")
                self._warned_not_connected = True
            return False
        
        if not self.dg_connection:
            logger.error("[ERROR] No Deepgram connection available")
            return False
        
        try:
            # Send audio to Deepgram for transcription
            await self.dg_connection.send(audio_chunk)
            
            # Clear warning flag on successful send
            if hasattr(self, '_warned_not_connected'):
                delattr(self, '_warned_not_connected')
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Error processing audio chunk: {e}")
            self._is_connected = False
            return False
    
    async def start_stream(self, callback) -> bool:
        """
        Start the STT stream with a specific callback.
        
        Args:
            callback: Async callback function for transcription events
            
        Returns:
            True if stream is active and callback set
        """
        if not self.is_connected:
            logger.error("[STT] Cannot start stream: Deepgram is not connected")
            return False
            
        self.callback_function = callback
        logger.info("[STT] Stream started with callback")
        return True

    async def close(self) -> bool:
        """
        Close STT connection and cleanup all resources.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        close_start = time.time()
        logger.info("[CLEANUP] Closing Deepgram STT service")
        
        try:
            # Log session duration
            if self.session_start_time:
                duration = time.time() - self.session_start_time
                logger.info(f"[SESSION] Deepgram session duration: {duration:.2f}s")
            
            # Clear processing state
            self.is_finals.clear()
            self.once = 0
            
            # Close WebSocket connection
            if self.dg_connection:
                try:
                    await self.dg_connection.finish()
                    logger.info("[CONNECTION] Deepgram connection finished")
                except Exception as finish_error:
                    logger.error(f"[ERROR] Error finishing connection: {finish_error}")
                
                self.dg_connection = None
            
            # Update connection status
            self._is_connected = False
            
            # Close Deepgram client to cleanup underlying sessions
            if self.deepgram_client:
                try:
                    if hasattr(self.deepgram_client, 'close'):
                        await self.deepgram_client.close()
                except Exception as client_error:
                    logger.error(f"[ERROR] Error closing Deepgram client: {client_error}")
            
            # Reset all state
            self._is_connected = False
            self.callback_function = None
            self.deepgram_client = None
            
            close_time = time.time() - close_start
            logger.info(f"[TIMING] Deepgram STT close took {close_time:.3f}s")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Error during Deepgram cleanup: {e}", exc_info=True)
            return False


# Convenience function for quick initialization
async def create_stt_service(api_key: str, callback=None) -> DeepgramSTTService:
    """
    Create and initialize a Deepgram STT service instance.
    
    Args:
        api_key: Deepgram API key
        callback: Optional async callback function for transcription events
        
    Returns:
        Initialized DeepgramSTTService instance
    """
    service = DeepgramSTTService(api_key=api_key)
    await service.initialize(api_key=api_key, callback=callback)
    
    logger.info("[FACTORY] Created and initialized STT service")
    return service
