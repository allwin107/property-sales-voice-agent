"""
Exotel Service - Telephony Integration
Handles Exotel phone calls, NCCO generation, and WebSocket streaming setup
"""
import logging
import asyncio
import base64
import json
import aiohttp
from typing import Dict, Optional
from services.telephony_base import BaseTelephonyService

logger = logging.getLogger(__name__)


class ExotelTelephonyService(BaseTelephonyService):
    """
    Exotel service for handling phone calls and generating NCCO for audio streaming
    """
    
    def __init__(
        self, 
        account_sid: str, 
        api_key: str, 
        api_token: str,
        subdomain: str = "api.exotel.com",
        webhook_url: str = ""
    ):
        """
        Initialize Exotel telephony service
        
        Args:
            account_sid: Exotel Account SID
            api_key: Exotel API Key
            api_token: Exotel API Token
            subdomain: Exotel API subdomain (default: api.exotel.com)
            webhook_url: Base webhook URL for callbacks
        """
        self.account_sid = account_sid
        self.api_key = api_key
        self.api_token = api_token
        self.subdomain = subdomain
        self.webhook_url = webhook_url
        
        # Create Basic Auth credentials
        credentials = f"{api_key}:{api_token}"
        self.auth_header = base64.b64encode(credentials.encode()).decode()
        
        logger.info(f"[EXOTEL] Initialized with subdomain: {subdomain}")
    
    async def make_call(
        self, 
        from_number: str, 
        to_number: str, 
        session_id: str
    ) -> Dict[str, str]:
        """
        Initiate an outbound call via Exotel API.
        
        Args:
            from_number: Caller ID / source number
            to_number: Destination phone number
            session_id: Unique session identifier
            
        Returns:
            Dict with keys: status, message, call_uuid, session_id
        """
        try:
            # Construct Exotel API endpoint
            url = f"https://{self.subdomain}/v1/Accounts/{self.account_sid}/Calls/connect.json"
            
            # Prepare payload
            payload = {
                "From": from_number,
                "To": to_number,
                "CallerId": from_number,
                "Url": f"{self.webhook_url}/exotel-webhook?session_id={session_id}",
                "TimeLimit": 3600,  # 1 hour max call duration
                "TimeOut": 30,       # 30 seconds ring timeout
                "CallType": "trans", # Transactional call
                "Record": "true"     # Enable call recording
            }
            
            # Make API request with Basic Auth
            headers = {
                "Authorization": f"Basic {self.auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            logger.info(f"[EXOTEL] Initiating call from {from_number} to {to_number}")
            logger.debug(f"[EXOTEL] Request URL: {url}")
            logger.debug(f"[EXOTEL] Payload: {payload}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, headers=headers) as response:
                    response_text = await response.text()
                    
                    if response.status == 200 or response.status == 201:
                        response_data = json.loads(response_text)
                        call_sid = response_data.get('Call', {}).get('Sid', '')
                        
                        logger.info(f"[EXOTEL] Call initiated successfully. SID: {call_sid}")
                        
                        return {
                            "status": "success",
                            "message": "Call initiated successfully",
                            "call_uuid": call_sid,
                            "session_id": session_id
                        }
                    else:
                        logger.error(f"[EXOTEL] API error {response.status}: {response_text}")
                        return {
                            "status": "error",
                            "message": f"API error: {response.status}",
                            "call_uuid": "",
                            "session_id": session_id
                        }
                        
        except Exception as e:
            logger.error(f"[EXOTEL] Error making call: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "call_uuid": "",
                "session_id": session_id
            }
    
    async def hangup_call(self, call_id: str) -> Dict[str, str]:
        """
        Terminate an active call via Exotel API.
        
        Args:
            call_id: Exotel Call SID
            
        Returns:
            Dict with keys: status, message
        """
        try:
            # Construct Exotel API endpoint
            url = f"https://{self.subdomain}/v1/Accounts/{self.account_sid}/Calls/{call_id}"
            
            # Payload to mark call as completed
            payload = {"Status": "completed"}
            
            headers = {
                "Authorization": f"Basic {self.auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            logger.info(f"[EXOTEL] Hanging up call: {call_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, headers=headers) as response:
                    response_text = await response.text()
                    
                    if response.status == 200 or response.status == 201:
                        logger.info(f"[EXOTEL] Call {call_id} terminated successfully")
                        return {
                            "status": "success",
                            "message": "Call terminated successfully"
                        }
                    else:
                        logger.error(f"[EXOTEL] Hangup error {response.status}: {response_text}")
                        return {
                            "status": "error",
                            "message": f"API error: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"[EXOTEL] Error hanging up call: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }
    
    # Note: Exotel streaming logic is handled via Exotel Applet configuration (using <Stream> verb).
    # This service does not generate flow control JSON like Vonage NCCO.
    def generate_stream_response(
        self, 
        ws_url: Optional[str] = None,
        ngrok_url: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Stub implementation for Exotel.
        Exotel uses Applets for flow control, so this method is not used.
        """
        return ""


# Convenience function for quick initialization
def create_exotel_service(
    account_sid: str,
    api_key: str,
    api_token: str,
    subdomain: str = "api.exotel.com",
    webhook_url: str = ""
) -> ExotelTelephonyService:
    """
    Create an Exotel telephony service instance.
    
    Args:
        account_sid: Exotel Account SID
        api_key: Exotel API Key
        api_token: Exotel API Token
        subdomain: Exotel API subdomain
        webhook_url: Base webhook URL
        
    Returns:
        ExotelTelephonyService instance
    """
    service = ExotelTelephonyService(
        account_sid=account_sid,
        api_key=api_key,
        api_token=api_token,
        subdomain=subdomain,
        webhook_url=webhook_url
    )
    
    logger.info("[FACTORY] Created Exotel telephony service")
    return service
