"""
Abstract base class for Speech-to-Text (STT) services.
Defines the interface that all STT providers must implement.
"""
from abc import ABC, abstractmethod
from typing import Callable, Optional


class BaseSTTService(ABC):
    """
    Abstract base class for Speech-to-Text services.
    
    All STT providers (Deepgram, Sarvam, etc.) must inherit from this class
    and implement all abstract methods.
    """
    
    @abstractmethod
    async def initialize(self, api_key: str, callback: Optional[Callable] = None) -> bool:
        """
        Initialize the STT service with API credentials.
        
        Args:
            api_key: API key for the STT provider
            callback: Optional callback function for transcription results
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def process_audio(self, audio_chunk: bytes) -> bool:
        """
        Process an audio chunk and send it to the STT service.
        
        Args:
            audio_chunk: Raw audio bytes to transcribe
            
        Returns:
            True if audio was successfully processed, False otherwise
        """
        pass
    
    @abstractmethod
    async def start_stream(self, callback: Callable) -> bool:
        """
        Start the audio streaming session with a callback for results.
        
        Args:
            callback: Function to call with transcription results
            
        Returns:
            True if stream started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def close(self) -> bool:
        """
        Close the STT service and clean up resources.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the STT service is currently connected and ready.
        
        Returns:
            True if connected, False otherwise
        """
        pass
