# Property Enquiry Voice Agent

An AI-powered voice agent that handles property enquiries with automated outbound calling capabilities. Built with FastAPI, Exotel, and GPT-4.

## Features

- **Web Form Submission**: Modern, responsive property enquiry form
- **Automated Outbound Calling**: Calls users 60 seconds after form submission
- **AI Conversation**: Natural language collection of property requirements:
  - Property type (apartment, villa, plot, commercial)
  - Budget range
  - Preferred location
  - Bedroom requirements
  - Purchase timeline
  - Specific requirements
- **Real-time Streaming**: WebSocket-based audio streaming via Exotel
- **Data Storage**: JSON-based storage of enquiries and conversation data
- **Multi-provider Support**: Supports Deepgram/Sarvam for STT and Cartesia/Sarvam for TTS

## Project Structure

```
property-agent/
├── main.py                 # FastAPI application
├── config.py              # Configuration management
├── prompts.py             # LLM system prompts
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── .env.example          # Environment template
├── static/
│   └── index.html        # Property enquiry form
├── data/
│   └── enquiries.json    # Stored enquiries (auto-created)
├── logs/                 # Application logs
├── services/             # Copied from hospital-receptionist
│   ├── stt_factory.py
│   ├── tts_factory.py
│   ├── llm_service.py
│   ├── telephony_factory.py
│   └── enquiry_storage.py  # Property-specific storage
└── utils/                # Copied from hospital-receptionist
```

## Setup

### 1. Install Dependencies

```bash
cd property-agent
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```env
# Required
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io  # Update with your ngrok URL
GROQ_API_KEY=your_groq_api_key
EXOTEL_ACCOUNT_SID=your_exotel_sid
EXOTEL_API_KEY=your_exotel_api_key
EXOTEL_API_TOKEN=your_exotel_token
EXOTEL_PHONE_NUMBER=your_exotel_number

# STT Provider (choose one)
STT_PROVIDER=deepgram  # or sarvam
DEEPGRAM_API_KEY=your_deepgram_key
SARVAM_API_KEY=your_sarvam_key

# TTS Provider (choose one)
TTS_PROVIDER=cartesia  # or sarvam
CARTESIA_API_KEY=your_cartesia_key
CARTESIA_VOICE_ID=your_voice_id

# Optional
CALL_DELAY_SECONDS=60  # Delay before calling (default: 60)
DEBUG=False
```

### 3. Start Ngrok (Required for Exotel webhooks)

```bash
ngrok http 8001
```

Update `WEBHOOK_BASE_URL` in `.env` with your ngrok URL.

### 4. Run the Application

```bash
python main.py
```

The application will start on `http://0.0.0.0:8001`

## Usage

### Submit Property Enquiry

1. Navigate to `http://localhost:8001`
2. Fill out the form:
   - Full Name (required)
   - Mobile Phone (required)
   - Email Address (required)
   - Message (optional)
3. Click "Submit Enquiry"
4. Wait 60 seconds for the automated call

### API Endpoints

- **GET /** - Property enquiry form (HTML)
- **POST /submit-enquiry** - Submit new enquiry
  ```json
  {
    "name": "John Doe",
    "phone": "+919876543210",
    "email": "john@example.com",
    "message": "Looking for 3BHK apartment"
  }
  ```
- **POST /exotel-webhook** - Exotel call webhook (internal)
- **WebSocket /exotel_stream** - Audio streaming endpoint (internal)
- **GET /enquiries** - List all enquiries (admin)
- **GET /health** - Service health check

### View Enquiries

```bash
curl http://localhost:8001/enquiries
```

## How It Works

1. **Form Submission**:
   - User submits property enquiry form
   - System generates unique `enquiry_id`
   - Saves data to `data/enquiries.json` with status "pending"
   - Schedules async call task

2. **Delayed Call Initiation**:
   - System waits `CALL_DELAY_SECONDS` (default: 60s)
   - Initiates Exotel outbound call via API
   - Updates enquiry status to "calling"

3. **Call Connection**:
   - Exotel calls the webhook endpoint
   - System returns WebSocket stream URL
   - WebSocket connection established

4. **Conversation Flow**:
   - AI greets user with personalized context
   - Collects property requirements via natural conversation
   - Stores collected data in real-time
   - Handles interruptions gracefully

5. **Call Completion**:
   - Session cleanup when call ends
   - Calculates call duration
   - Updates status to "completed"
   - Saves final conversation data

## Data Storage

Enquiries are stored in `data/enquiries.json`:

```json
[
  {
    "enquiry_id": "unique-uuid",
    "form_data": {
      "name": "John Doe",
      "phone": "+919876543210",
      "email": "john@example.com",
      "message": "Looking for 3BHK apartment"
    },
    "submitted_at": "2026-02-11T17:00:00",
    "status": "completed",
    "call_sid": "exotel-call-id",
    "call_data": {
      "collected_info": {
        "property_type": "apartment",
        "budget_range": "50-70 lakhs",
        "location": "Whitefield",
        "bedrooms": "3",
        "timeline": "3-6 months",
        "requirements": "parking, gym"
      },
      "conversation_history": [...],
      "duration": 120.5,
      "ended_at": "2026-02-11T17:02:00"
    }
  }
]
```

## Customization

### Agent Persona

Edit `config.py`:

```python
AGENT_NAME = "Alex"        # Change agent name
COMPANY_NAME = "PropFinder"  # Change company name
```

### System Prompt

Edit `prompts.py` to customize conversation style and collection flow.

### Dynamic Fields

Edit `PROPERTY_DYNAMIC_FIELDS` in `main.py` to add/modify data collection fields.

## Troubleshooting

### Call Not Initiated

- Check Exotel credentials in `.env`
- Verify phone number format (E.164)
- Check logs for API errors

### WebSocket Connection Failed

- Ensure ngrok is running
- Verify `WEBHOOK_BASE_URL` is correct
- Check firewall settings

### Audio Issues (TTS/STT)

- Verify API keys for chosen providers
- Check provider selection in `.env`
- Monitor logs for service errors

## Development

### Run in Debug Mode

```bash
DEBUG=True python main.py
```

### Test Without Calling

Reduce delay for testing:

```env
CALL_DELAY_SECONDS=5
```

## License

MIT

## Support

For issues or questions, contact support or check the logs in `logs/` directory.
