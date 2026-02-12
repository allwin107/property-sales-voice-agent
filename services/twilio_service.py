"""
Twilio Service - Telephony Integration
Handles Twilio phone calls, TwiML generation, and WebSocket streaming setup
"""
import logging
import asyncio
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from services.telephony_base import BaseTelephonyService
import config

logger = logging.getLogger(__name__)


class TwilioTelephonyService(BaseTelephonyService):
    """
    Twilio service for handling phone calls and generating TwiML for audio streaming
    """
    
    def __init__(self, account_sid: str, auth_token: str, phone_number: str):
        """
        Initialize Twilio telephony service
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            phone_number: Twilio phone number to use
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.phone_number = phone_number
        self.client = Client(account_sid, auth_token)
        
        logger.info(f"[TWILIO] Service initialized with account: {account_sid[:10]}...")
        logger.info(f"[TWILIO] Phone number: {phone_number}")
    
    def generate_stream_response(self, session_id: str) -> str:
        """
        Generate TwiML response for inbound calls with WebSocket streaming.
        
        Args:
            session_id: Unique session identifier for this call
            
        Returns:
            TwiML XML string for Twilio to execute
        """
        try:
            logger.info(f"[TWILIO] Generating stream response for session: {session_id}")
            
            # Get the WebSocket URL from config
            # Convert HTTP/HTTPS webhook URL to WSS WebSocket URL
            webhook_base = config.WEBHOOK_BASE_URL
            
            # Replace http/https with wss for WebSocket
            if webhook_base.startswith('https://'):
                ws_base = webhook_base.replace('https://', 'wss://')
            elif webhook_base.startswith('http://'):
                ws_base = webhook_base.replace('http://', 'wss://')
            else:
                ws_base = f"wss://{webhook_base}"
            
            # Create WebSocket URL for Twilio stream
            twilio_ws_url = f"{ws_base}/twilio_stream"
            
            logger.info(f"[TWILIO] WebSocket URL: {twilio_ws_url}")
            
            # Create TwiML response
            response = VoiceResponse()
            
            # Optional: Add greeting before connecting to stream
            # response.say(
            #     "Welcome to City General Hospital. Connecting you to our AI receptionist.",
            #     voice="Polly.Joanna"
            # )
            
            # Create Connect element for WebSocket streaming
            connect = Connect()
            
            # Create Stream element with WebSocket URL
            stream = Stream(url=twilio_ws_url)
            
            # Add session_id as a custom parameter to the stream
            stream.parameter(name="session_id", value=session_id)
            
            # Add stream to connect
            connect.append(stream)
            
            # Add connect to response
            response.append(connect)
            
            # Convert to XML string
            xml_response = str(response)
            
            logger.info(f"[TWILIO] Generated TwiML for session {session_id}")
            logger.debug(f"[TWILIO] TwiML content: {xml_response}")
            
            return xml_response
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate stream response: {e}", exc_info=True)
            
            # Fallback TwiML in case of error
            response = VoiceResponse()
            response.say(
                "We're experiencing technical difficulties. Please try again later.",
                voice="Polly.Joanna"
            )
            response.hangup()
            return str(response)
    
    async def make_call(self, to_number: str, session_id: str) -> dict:
        """
        Make an outbound call with Twilio (e.g., for appointment reminders).
        
        Args:
            to_number: Phone number to call
            session_id: Unique session identifier
            
        Returns:
            Dictionary with call status and details
        """
        try:
            logger.info(f"[TWILIO] Making outbound call to {to_number} (session: {session_id})")
            
            # Create webhook URL with session_id
            webhook_url = f"{config.WEBHOOK_BASE_URL}/webhook?session_id={session_id}"
            
            logger.info(f"[TWILIO] Using webhook URL: {webhook_url}")
            
            # Run the blocking Twilio API call in executor
            loop = asyncio.get_event_loop()
            call = await loop.run_in_executor(
                None,
                lambda: self.client.calls.create(
                    url=webhook_url,
                    to=to_number,
                    from_=self.phone_number,
                    method="POST",
                    record=True,
                    recording_status_callback=f"{config.WEBHOOK_BASE_URL}/recording",
                    recording_status_callback_method="POST"
                )
            )
            
            call_sid = call.sid
            logger.info(f"[TWILIO] Call initiated successfully - SID: {call_sid}")
            
            return {
                "status": "success",
                "message": "Call initiated",
                "call_sid": call_sid,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to make call: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def hangup_call(self, call_sid: str) -> dict:
        """
        Hang up an active call.
        
        Args:
            call_sid: Twilio Call SID to terminate
            
        Returns:
            Dictionary with hangup status
        """
        try:
            logger.info(f"[TWILIO] Hanging up call: {call_sid}")
            
            # Run blocking Twilio API call in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.calls(call_sid).update(status='completed')
            )
            
            logger.info(f"[TWILIO] Call {call_sid} terminated successfully")
            
            return {
                "status": "success",
                "message": "Call terminated"
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to hang up call: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def send_sms(self, to_number: str, message: str) -> dict:
        """
        Send SMS message (for appointment confirmations).
        
        Args:
            to_number: Recipient phone number
            message: Message text to send
            
        Returns:
            Dictionary with SMS status
        """
        try:
            logger.info(f"[TWILIO] Sending SMS to {to_number}")
            logger.debug(f"[TWILIO] SMS content: {message[:100]}...")
            
            # Run blocking Twilio API call in executor
            loop = asyncio.get_event_loop()
            sms = await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    to=to_number,
                    from_=self.phone_number,
                    body=message
                )
            )
            
            message_sid = sms.sid
            logger.info(f"[TWILIO] SMS sent successfully - SID: {message_sid}")
            
            return {
                "status": "success",
                "message": "SMS sent",
                "message_sid": message_sid
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to send SMS: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }


# Convenience function for quick initialization
def create_twilio_service(
    account_sid: str = None,
    auth_token: str = None,
    phone_number: str = None
) -> TwilioTelephonyService:
    """
    Create a Twilio telephony service instance.
    
    Args:
        account_sid: Twilio Account SID (uses config if None)
        auth_token: Twilio Auth Token (uses config if None)
        phone_number: Twilio phone number (uses config if None)
        
    Returns:
        TwilioTelephonyService instance
    """
    account_sid = account_sid or config.TWILIO_ACCOUNT_SID
    auth_token = auth_token or config.TWILIO_AUTH_TOKEN
    phone_number = phone_number or config.TWILIO_PHONE_NUMBER
    
    service = TwilioTelephonyService(
        account_sid=account_sid,
        auth_token=auth_token,
        phone_number=phone_number
    )
    
    logger.info("[FACTORY] Created Twilio service")
    return service


# Compatibility alias
TwilioService = TwilioTelephonyService
