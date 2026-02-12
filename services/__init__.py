"""
Services package for Hospital Receptionist AI
Contains all external service integrations
"""
from .llm_service import GroqLLMService, create_llm_service
from .stt_service import DeepgramSTTService, create_stt_service
from .tts_service import CartesiaTTSService, create_tts_service
from .twilio_service import TwilioTelephonyService, create_twilio_service
from .exotel_service import ExotelTelephonyService, create_exotel_service

# Factory classes
from .stt_factory import STTServiceFactory
from .tts_factory import TTSServiceFactory
from .telephony_factory import TelephonyServiceFactory

# Base classes for extensibility
from .stt_base import BaseSTTService
from .tts_base import BaseTTSService
from .telephony_base import BaseTelephonyService

__all__ = [
    "GroqLLMService",
    "create_llm_service",
    "DeepgramSTTService",
    "create_stt_service",
    "CartesiaTTSService",
    "create_tts_service",
    "TwilioTelephonyService",
    "create_twilio_service",
    "ExotelTelephonyService",
    "create_exotel_service",
    "STTServiceFactory",
    "TTSServiceFactory",
    "TelephonyServiceFactory",
    "BaseSTTService",
    "BaseTTSService",
    "BaseTelephonyService",
]
