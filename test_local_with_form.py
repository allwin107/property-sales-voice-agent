"""
Property Enquiry Agent - Local Testing with Form Submission

This script provides the complete flow:
1. Submit form via web browser
2. Wait 60 seconds (configurable)
3. Voice conversation starts via mic/speaker

No Exotel needed - all local testing.
"""
import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

import config
from test_local import LocalVoiceClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Property Enquiry Agent - Local Test")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Active voice session
active_session = None
pending_enquiries = []


class EnquirySubmission(BaseModel):
    name: str
    phone: str
    email: str
    message: str = ""


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the enquiry form."""
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()


@app.post("/submit-enquiry")
async def submit_enquiry(enquiry: EnquirySubmission):
    """Handle form submission and schedule local voice session."""
    
    logger.info(f"Form submitted: {enquiry.name} - {enquiry.phone}")
    print(f"\n{'='*60}")
    print(f"FORM SUBMITTED")
    print(f"{'='*60}")
    print(f"Name: {enquiry.name}")
    print(f"Phone: {enquiry.phone}")
    print(f"Email: {enquiry.email}")
    print(f"Message: {enquiry.message}")
    print(f"{'='*60}\n")
    
    # Store enquiry data
    enquiry_data = {
        "name": enquiry.name,
        "phone": enquiry.phone,
        "email": enquiry.email,
        "message": enquiry.message,
        "submitted_at": datetime.now().isoformat()
    }
    pending_enquiries.append(enquiry_data)
    
    # Schedule voice session
    delay = config.CALL_DELAY_SECONDS
    print(f"[SCHEDULE] Voice session will start in {delay} seconds...")
    print(f"[SCHEDULE] Make sure your microphone and speakers are ready!")
    print(f"{'='*60}\n")
    
    asyncio.create_task(start_voice_session_after_delay(enquiry_data, delay))
    
    return {
        "status": "success",
        "message": f"Voice session will start in {delay} seconds",
        "delay": delay
    }


async def start_voice_session_after_delay(enquiry_data: dict, delay: int):
    """Wait for delay, then start local voice session."""
    global active_session
    
    try:
        # Countdown
        for remaining in range(delay, 0, -1):
            if remaining % 10 == 0 or remaining <= 5:
                print(f"[COUNTDOWN] Voice session starting in {remaining} seconds...")
            await asyncio.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"STARTING VOICE SESSION")
        print(f"{'='*60}")
        print(f"User: {enquiry_data['name']}")
        print(f"Enquiry: {enquiry_data['message']}")
        print(f"{'='*60}\n")
        
        # Create and start voice client with actual form data
        client = LocalVoiceClient(
            user_name=enquiry_data['name'],
            user_message=enquiry_data['message']
        )
        
        active_session = client
        
        # Start the voice session
        await client.start_session()
        
        print(f"\n{'='*60}")
        print(f"VOICE SESSION COMPLETED")
        print(f"{'='*60}\n")
        
        active_session = None
        
    except Exception as e:
        logger.error(f"Error in voice session: {e}", exc_info=True)
        print(f"\nERROR: Voice session failed - {e}\n")
        active_session = None


@app.get("/status")
async def get_status():
    """Check if voice session is active."""
    return {
        "active_session": active_session is not None,
        "pending_enquiries": len(pending_enquiries),
        "delay_seconds": config.CALL_DELAY_SECONDS
    }


@app.on_event("startup")
async def startup():
    """Display startup information."""
    print("\n" + "=" * 60)
    print("BRIGADE ETERNIA VOICE AGENT - LOCAL TEST MODE")
    print("=" * 60)
    print(f"Agent: {config.AGENT_NAME} from {config.COMPANY_NAME}")
    print(f"Project: {config.PROJECT_NAME}")
    print(f"STT: {config.STT_PROVIDER.upper()}")
    print(f"TTS: {config.TTS_PROVIDER.upper()}")
    print(f"Delay: {config.CALL_DELAY_SECONDS} seconds")
    print("=" * 60)
    print(f"\nServer starting on: http://localhost:{config.PORT}")
    print("\nInstructions:")
    print("1. Open browser: http://localhost:8001")
    print("2. Fill out the Brigade Eternia enquiry form")
    print("3. Click 'Submit Enquiry'")
    print(f"4. Wait {config.CALL_DELAY_SECONDS} seconds")
    print("5. Voice conversation will start automatically")
    print("6. Speak into your microphone!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    print("\nStarting Brigade Eternia Voice Agent - Local Test Server...\n")
    uvicorn.run(app, host=config.HOST, port=config.PORT)
