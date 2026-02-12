import asyncio
import logging
import uuid
import base64
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import prompts
from services.stt_factory import STTServiceFactory
from services.tts_factory import TTSServiceFactory
from services.llm_service import GroqLLMService
from services.telephony_factory import TelephonyServiceFactory
from services.enquiry_storage import EnquiryStorage
from services.knowledge_validator import KnowledgeValidator

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Property Enquiry Agent")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global state
active_sessions = {}
storage = EnquiryStorage(config.ENQUIRIES_FILE)
telephony_service = None

# Dynamic fields for Brigade Eternia site visit flow
BRIGADE_ETERNIA_DYNAMIC_FIELDS = {
    "user_confirmed_identity": {
        "type": "string",
        "description": "yes or no",
        "default": "none"
    },
    "wants_site_visit": {
        "type": "string", 
        "description": "yes, no, maybe, or none",
        "default": "none"
    },
    "wants_details_first": {
        "type": "string",
        "description": "yes or no",
        "default": "none"  
    },
    "visit_date": {
        "type": "string",
        "description": "Date user wants to visit (e.g., 'Saturday', 'Feb 15')",
        "default": "none"
    },
    "visit_time": {
        "type": "string",
        "description": "Time slot (e.g., '10 AM', '3 PM', 'morning', 'evening')",
        "default": "none"
    },
    "visit_booking_attempts": {
        "type": "string",
        "description": "Number of times asked: 1, 2, 3",
        "default": "none"
    },
    "budget_range": {
        "type": "string",
        "description": "Budget interest",
        "default": "none"
    },
    "preferred_bhk": {
        "type": "string",
        "description": "3 BHK or 4 BHK",
        "default": "none"
    }
}

class EnquirySubmission(BaseModel):
    name: str
    phone: str
    email: str
    message: str = ""

@app.on_event("startup")
async def startup():
    global telephony_service
    
    logger.info("=" * 80)
    logger.info("BRIGADE ETERNIA VOICE AGENT")
    logger.info(f"Project: {config.PROJECT_NAME}")
    logger.info(f"Agent: {config.AGENT_NAME}")
    logger.info(f"Telephony: Exotel")
    logger.info("=" * 80)
    
    # Initialize telephony service
    telephony_service = TelephonyServiceFactory.create(
        provider=config.TELEPHONY_PROVIDER,
        account_sid=config.EXOTEL_ACCOUNT_SID,
        api_key=config.EXOTEL_API_KEY,
        api_token=config.EXOTEL_API_TOKEN,
        subdomain=config.EXOTEL_SUBDOMAIN,
        webhook_url=config.WEBHOOK_BASE_URL
    )
    
    logger.info(f"STT: {config.STT_PROVIDER}, TTS: {config.TTS_PROVIDER}")
    logger.info(f"Call delay: {config.CALL_DELAY_SECONDS}s")
    logger.info("=" * 80)

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.post("/submit-enquiry")
async def submit_enquiry(enquiry: EnquirySubmission):
    enquiry_id = str(uuid.uuid4())
    
    enquiry_data = {
        "enquiry_id": enquiry_id,
        "form_data": {
            "name": enquiry.name,
            "phone": enquiry.phone,
            "email": enquiry.email,
            "message": enquiry.message
        },
        "submitted_at": datetime.now().isoformat(),
        "call_data": None,
        "status": "pending"
    }
    
    await storage.save_enquiry(enquiry_data)
    logger.info(f"Enquiry submitted: {enquiry_id} - {enquiry.name}")
    
    # Schedule call
    asyncio.create_task(schedule_call(enquiry_id, enquiry.phone))
    
    return {"status": "success", "enquiry_id": enquiry_id, "message": "Call scheduled"}

async def schedule_call(enquiry_id: str, phone: str):
    logger.info(f"Scheduling call for {enquiry_id} in {config.CALL_DELAY_SECONDS}s")
    await asyncio.sleep(config.CALL_DELAY_SECONDS)
    
    logger.info(f"Initiating call to {phone}")
    # Exotel Strategy: Call Customer (From) -> Connect to Virtual Number (To) which holds the Applet/Flow
    result = await telephony_service.make_call(
        from_number=phone,
        to_number=config.EXOTEL_PHONE_NUMBER,
        session_id=enquiry_id
    )
    
    if result["status"] == "success":
        await storage.update_enquiry(enquiry_id, {
            "status": "calling",
            "call_sid": result.get("call_uuid")
        })
        logger.info(f"Call initiated: {result.get('call_uuid')}")
    else:
        logger.error(f"Call failed: {result.get('message')}")
        await storage.update_enquiry(enquiry_id, {"status": "failed"})

@app.api_route("/exotel-webhook", methods=["GET", "POST"])
async def exotel_webhook(request: Request):
    session_id = request.query_params.get("session_id")
    logger.info(f"Exotel webhook for session: {session_id}")
    
    # Just log the event as we use Applet for logic
    try:
        data = await request.json()
        logger.info(f"Webhook Payload: {data}")
    except:
        body = await request.body()
        logger.info(f"Webhook Body: {body.decode()}")
    
    return JSONResponse(content={"status": "ok"})

@app.websocket("/exotel_stream")
async def exotel_stream(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    
    try:
        # Get session_id from first message or headers
        message = await websocket.receive_text()
        data = json.loads(message)
        session_id = data.get("session_id") or data.get("headers", {}).get("session_id")
        
        logger.info(f"WebSocket connected: {session_id}")
        
        # Initialize session
        await initialize_call_session(session_id, websocket)
        
        # Handle audio stream
        async for message in websocket.iter_text():
            data = json.loads(message)
            
            if data.get("event") == "media":
                audio_chunk = base64.b64decode(data["media"]["payload"])
                session = active_sessions.get(session_id)
                if session:
                    await session["stt_service"].process_audio(audio_chunk)
            
            elif data.get("event") == "stop":
                await cleanup_session(session_id)
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        await websocket.close()

async def initialize_call_session(session_id: str, websocket: WebSocket):
    logger.info(f"Initializing session: {session_id}")
    
    # Get enquiry data
    enquiry = await storage.get_enquiry(session_id)
    if not enquiry:
        logger.error(f"Enquiry not found: {session_id}")
        return
    
    form_data = enquiry["form_data"]
    
    # Initialize services
    stt_api_key = (
        config.DEEPGRAM_API_KEY if config.STT_PROVIDER == 'deepgram'
        else config.SARVAM_API_KEY
    )
    tts_api_key = (
        config.CARTESIA_API_KEY if config.TTS_PROVIDER == 'cartesia'
        else config.SARVAM_API_KEY
    )
    
    stt_service = STTServiceFactory.create(
        provider=config.STT_PROVIDER,
        api_key=stt_api_key
    )
    
    tts_kwargs = {}
    if config.TTS_PROVIDER == 'cartesia':
        tts_kwargs = {'model_id': 'sonic-english', 'speed': 'normal'}
    
    tts_service = TTSServiceFactory.create(
        provider=config.TTS_PROVIDER,
        api_key=tts_api_key,
        voice_id=config.CARTESIA_VOICE_ID if config.TTS_PROVIDER == 'cartesia' else 'meera',
        **tts_kwargs
    )
    
    llm_service = GroqLLMService(api_key=config.GROQ_API_KEY, max_history=10)
    
    # Initialize all services
    await stt_service.initialize(
        api_key=stt_api_key,
        callback=lambda text: handle_transcription(text, session_id)
    )
    await tts_service.initialize()
    
    # Get system prompt
    system_prompt = prompts.get_formatted_prompt(
        user_name=form_data["name"],
        user_message=form_data["message"]
    )
    
    await llm_service.initialize(
        dynamic_fields=BRIGADE_ETERNIA_DYNAMIC_FIELDS,
        system_prompt_template=system_prompt
    )
    
    # Store session
    active_sessions[session_id] = {
        "session_id": session_id,
        "websocket": websocket,
        "stt_service": stt_service,
        "tts_service": tts_service,
        "llm_service": llm_service,
        "conversation_history": [],
        "start_time": datetime.now(),
        "enquiry_data": enquiry
    }
    
    # Send greeting with first name only
    first_name = form_data['name'].strip().split()[0] if form_data['name'] else "there"
    greeting = f"Hi, am I speaking with {first_name}?"
    
    await tts_service.synthesize(
        text=greeting,
        send_audio_callback=lambda chunk, action: send_audio_to_exotel(websocket, chunk, action)
    )

async def handle_transcription(text: str, session_id: str):
    if text == "__FORCE_STOP__":
        session = active_sessions.get(session_id)
        if session:
            await session["tts_service"].stop()
        return
    
    session = active_sessions.get(session_id)
    if not session:
        return
    
    logger.info(f"[{session_id}] User: {text}")
    
    # Stop TTS
    await session["tts_service"].stop()
    
    # Add to history
    session["conversation_history"].append({"role": "user", "content": text})
    
    # Get LLM response
    response = await session["llm_service"].generate_response(
        user_input=text,
        conversation_history=session["conversation_history"]
    )
    
    ai_text = response["response"].response
    collected_data = response["raw_model_data"]
    
    logger.info(f"[{session_id}] AI: {ai_text}")
    logger.info(f"[{session_id}] Collected: {collected_data}")
    
    # Check if site visit booked
    if collected_data.get("visit_date") != "none" and collected_data.get("visit_time") != "none":
        logger.info(f"[{session_id}] Site visit booked: {collected_data['visit_date']} at {collected_data['visit_time']}")
        
        # Mark as success
        await storage.update_enquiry(session_id, {
            "status": "site_visit_booked",
            "visit_scheduled": {
                "date": collected_data["visit_date"],
                "time": collected_data["visit_time"]
            },
            "call_data": {
                "collected_info": collected_data,
                "conversation_history": session["conversation_history"]
            }
        })
        
        # This will be the final message, end call after TTS
        session["ending_soon"] = True
    
    # Add to history
    session["conversation_history"].append({"role": "assistant", "content": ai_text})
    
    # Save collected data (if not already saved above)
    if not session.get("ending_soon"):
        await storage.update_enquiry(session_id, {
            "call_data": {
                "collected_info": collected_data,
                "conversation_history": session["conversation_history"]
            }
        })
    
    # Synthesize response
    await session["tts_service"].synthesize(
        text=ai_text,
        send_audio_callback=lambda chunk, action: send_audio_to_exotel(session["websocket"], chunk, action)
    )
    
    # Check if we should end
    if session.get("ending_soon") or response["should_end_call"]:
        await asyncio.sleep(2)
        await cleanup_session(session_id)

async def send_audio_to_exotel(websocket: WebSocket, audio_chunk, action: str):
    if action == "playAudio" and audio_chunk:
        await websocket.send_json({
            "event": "media",
            "media": {
                "payload": base64.b64encode(audio_chunk).decode()
            }
        })
    elif action == "clearAudio":
        await websocket.send_json({"event": "clear"})

async def cleanup_session(session_id: str):
    session = active_sessions.get(session_id)
    if not session:
        return
    
    logger.info(f"Cleaning up session: {session_id}")
    
    # Close services
    await session["stt_service"].close()
    await session["tts_service"].close()
    await session["llm_service"].close()
    
    # Calculate duration
    duration = (datetime.now() - session["start_time"]).total_seconds()
    
    # Update storage
    await storage.update_enquiry(session_id, {
        "status": "completed",
        "call_data": {
            **session["enquiry_data"].get("call_data", {}),
            "duration": duration,
            "ended_at": datetime.now().isoformat()
        }
    })
    
    del active_sessions[session_id]
    logger.info(f"Session cleaned: {session_id}")

@app.get("/enquiries")
async def get_enquiries():
    enquiries = await storage.get_all_enquiries()
    return {"enquiries": enquiries}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "provider": config.TELEPHONY_PROVIDER
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
