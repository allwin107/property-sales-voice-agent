import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Application
APP_NAME = "Brigade Eternia Voice Agent"
HOST = "0.0.0.0"
PORT = 8001  # Different port from hospital
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Webhook
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_VOICE_ID = os.getenv("SARVAM_VOICE_ID", "rohan")
SARVAM_MODEL = os.getenv("SARVAM_MODEL", "bulbul:v3")

# Exotel
EXOTEL_ACCOUNT_SID = os.getenv("EXOTEL_ACCOUNT_SID", "")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY", "")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN", "")
EXOTEL_SUBDOMAIN = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.com")
EXOTEL_PHONE_NUMBER = os.getenv("EXOTEL_PHONE_NUMBER", "")

# Service Providers
STT_PROVIDER = os.getenv("STT_PROVIDER", "deepgram")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "cartesia")
TELEPHONY_PROVIDER = "exotel"  # Fixed for this project

# LLM Settings
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "300"))
LLM_MAX_HISTORY = int(os.getenv("LLM_MAX_HISTORY", "10"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_RETRY_DELAY = int(os.getenv("LLM_RETRY_DELAY", "2"))
GROQ_URL = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
# STT - Deepgram Settings
DEEPGRAM_MODEL = os.getenv("DEEPGRAM_MODEL", "nova-3")
DEEPGRAM_LANGUAGE = os.getenv("DEEPGRAM_LANGUAGE", "en")
DEEPGRAM_SAMPLE_RATE = int(os.getenv("DEEPGRAM_SAMPLE_RATE", "8000"))
DEEPGRAM_ENDPOINTING = int(os.getenv("DEEPGRAM_ENDPOINTING", "100"))

# STT - Sarvam Settings
SARVAM_STT_URL = os.getenv("SARVAM_STT_URL", "wss://api.sarvam.ai/speech-to-text-translate")

# TTS - Cartesia Settings
CARTESIA_MODEL_ID = os.getenv("CARTESIA_MODEL_ID", "sonic-english")
CARTESIA_SPEED = os.getenv("CARTESIA_SPEED", "normal")

# TTS - Sarvam Settings
SARVAM_LANGUAGE = os.getenv("SARVAM_LANGUAGE", "hi-IN")
SARVAM_SPEED = float(os.getenv("SARVAM_SPEED", "1.1"))
SARVAM_TTS_URL = os.getenv("SARVAM_TTS_URL", "https://api.sarvam.ai/text-to-speech")

# Call Settings
CALL_DELAY_SECONDS = int(os.getenv("CALL_DELAY_SECONDS", "5"))

# Data Storage
ENQUIRIES_FILE = "data/enquiries.json"

# Brigade Eternia Settings
PROJECT_NAME = "Brigade Eternia"
AGENT_NAME = "Rohan"
COMPANY_NAME = "JLL Homes"
DEVELOPER_NAME = "Brigade Group"
KNOWLEDGE_BASE_PATH = "knowledge/brigade_eternia.json"
