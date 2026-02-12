"""
Abstract base class for Text-to-Speech (TTS) services.
Defines the interface that all TTS providers must implement.
"""
from abc import ABC, abstractmethod
from typing import Callable, Optional


class BaseTTSService(ABC):
    """
    Abstract base class for Text-to-Speech services.
    
    All TTS providers (Cartesia, Sarvam, etc.) must inherit from this class
    and implement all abstract methods.
    """
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the TTS service and prepare for synthesis.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def synthesize(
        self, 
        text: str, 
        send_audio_callback: Callable, 
        speed: Optional[str] = None
    ) -> bool:
        """
        Synthesize text to speech and stream audio via callback.
        
        Args:
            text: Text to convert to speech
            send_audio_callback: Function to call with audio chunks
            speed: Optional speed/pace parameter
            
        Returns:
            True if synthesis successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def stop(self):
        """
        Stop the current synthesis operation (interruption).
        """
        pass
    
    @abstractmethod
    async def close(self):
        """
        Close the TTS service and clean up resources.
        """
        pass
    
    @abstractmethod
    def set_speed(self, speed: str):
        """
        Set the speech speed/pace.
        
        Args:
            speed: Speed parameter (format varies by provider)
        """
        pass
    
    @abstractmethod
    async def get_last_spoken_text(self) -> str:
        """
        Get the last text that was synthesized.
        
        Returns:
            The last spoken text string
        """
        pass
