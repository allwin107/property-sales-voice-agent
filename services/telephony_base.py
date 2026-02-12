"""
Abstract base class for Telephony services.
Defines the interface that all telephony providers must implement.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseTelephonyService(ABC):
    """
    Abstract base class for Telephony services.
    
    All telephony providers (Twilio, Exotel, etc.) must inherit from this class
    and implement all abstract methods.
    """
    
    @abstractmethod
    async def make_call(
        self, 
        from_number: str, 
        to_number: str, 
        session_id: str
    ) -> Dict[str, str]:
        """
        Initiate an outbound call.
        
        Args:
            from_number: Caller ID / source number
            to_number: Destination phone number
            session_id: Unique session identifier
            
        Returns:
            Dict with keys: status, message, call_uuid, session_id
        """
        pass
    
    @abstractmethod
    async def hangup_call(self, call_id: str) -> Dict[str, str]:
        """
        Terminate an active call.
        
        Args:
            call_id: Call identifier (SID/UUID)
            
        Returns:
            Dict with keys: status, message
        """
        pass
    
    @abstractmethod
    def generate_stream_response(
        self, 
        ws_url: Optional[str] = None,
        ngrok_url: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Generate provider-specific response for WebSocket streaming.
        
        Args:
            ws_url: WebSocket URL (optional, provider may construct it)
            ngrok_url: ngrok base URL
            session_id: Session identifier
            
        Returns:
            Provider-specific response (TwiML XML, NCCO JSON, etc.)
        """
        pass
