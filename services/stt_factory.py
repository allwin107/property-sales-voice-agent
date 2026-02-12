"""
STT Service Factory
Provides factory pattern for creating Speech-to-Text service instances
"""
import logging
from typing import Dict, Type
from services.stt_base import BaseSTTService
from services.stt_service import DeepgramSTTService
from services.sarvam_stt_service import SarvamSTTService

logger = logging.getLogger(__name__)


class STTServiceFactory:
    """
    Factory class for creating STT service instances.
    Supports multiple providers with runtime selection.
    """
    
    # Provider registry
    _providers: Dict[str, Type[BaseSTTService]] = {
        'deepgram': DeepgramSTTService,
        'sarvam': SarvamSTTService
    }
    
    @classmethod
    def create(cls, provider: str, api_key: str, **kwargs) -> BaseSTTService:
        """
        Create an STT service instance for the specified provider.
        
        Args:
            provider: Provider name ('deepgram', 'sarvam')
            api_key: API key for the provider
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Instance of BaseSTTService
            
        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()
        
        if provider not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unsupported STT provider: '{provider}'. "
                f"Available providers: {available}"
            )
        
        service_class = cls._providers[provider]
        service = service_class(api_key=api_key, **kwargs)
        
        logger.info(f"[FACTORY] Created {provider} STT service instance")
        return service
    
    @classmethod
    def register_provider(cls, name: str, service_class: Type[BaseSTTService]):
        """
        Register a new STT provider.
        
        Args:
            name: Provider name (lowercase)
            service_class: Service class implementing BaseSTTService
            
        Raises:
            TypeError: If service_class doesn't inherit from BaseSTTService
        """
        if not issubclass(service_class, BaseSTTService):
            raise TypeError(
                f"Service class must inherit from BaseSTTService, "
                f"got {service_class.__name__}"
            )
        
        name = name.lower()
        cls._providers[name] = service_class
        logger.info(f"[FACTORY] Registered STT provider: {name}")
    
    @classmethod
    def list_providers(cls) -> list:
        """
        Get list of available STT providers.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
