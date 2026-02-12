"""
Telephony Service Factory
Provides factory pattern for creating Telephony service instances
"""
import logging
from typing import Dict, Type
from services.telephony_base import BaseTelephonyService
from services.twilio_service import TwilioTelephonyService
from services.exotel_service import ExotelTelephonyService

logger = logging.getLogger(__name__)


class TelephonyServiceFactory:
    """
    Factory class for creating Telephony service instances.
    Supports multiple providers with runtime selection.
    """
    
    # Provider registry
    _providers: Dict[str, Type[BaseTelephonyService]] = {
        'twilio': TwilioTelephonyService,
        'exotel': ExotelTelephonyService
    }
    
    @classmethod
    def create(cls, provider: str, **kwargs) -> BaseTelephonyService:
        """
        Create a Telephony service instance for the specified provider.
        
        Args:
            provider: Provider name ('twilio', 'exotel')
            **kwargs: Provider-specific arguments
                     For Twilio: account_sid, auth_token, phone_number
                     For Exotel: account_sid, api_key, api_token, subdomain, webhook_url
            
        Returns:
            Instance of BaseTelephonyService
            
        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()
        
        if provider not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unsupported Telephony provider: '{provider}'. "
                f"Available providers: {available}"
            )
        
        service_class = cls._providers[provider]
        service = service_class(**kwargs)
        
        logger.info(f"[FACTORY] Created {provider} Telephony service instance")
        return service
    
    @classmethod
    def register_provider(cls, name: str, service_class: Type[BaseTelephonyService]):
        """
        Register a new Telephony provider.
        
        Args:
            name: Provider name (lowercase)
            service_class: Service class implementing BaseTelephonyService
            
        Raises:
            TypeError: If service_class doesn't inherit from BaseTelephonyService
        """
        if not issubclass(service_class, BaseTelephonyService):
            raise TypeError(
                f"Service class must inherit from BaseTelephonyService, "
                f"got {service_class.__name__}"
            )
        
        name = name.lower()
        cls._providers[name] = service_class
        logger.info(f"[FACTORY] Registered Telephony provider: {name}")
    
    @classmethod
    def list_providers(cls) -> list:
        """
        Get list of available Telephony providers.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
