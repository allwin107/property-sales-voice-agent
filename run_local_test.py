"""
Local Test Runner for Property Enquiry Agent

Simple CLI to start local voice testing without telephony.
"""
import asyncio
import sys

# Add parent directory to path
sys.path.insert(0, '.')

from test_local import LocalVoiceClient
import config


async def main():
    """Main entry point for local testing."""
    print("\n" + "=" * 60)
    print("BRIGADE ETERNIA VOICE AGENT - LOCAL TEST MODE")
    print("=" * 60)
    print(f"Agent: {config.AGENT_NAME} from {config.COMPANY_NAME}")
    print(f"Project: {config.PROJECT_NAME}")
    print(f"STT Provider: {config.STT_PROVIDER.upper()}")
    print(f"TTS Provider: {config.TTS_PROVIDER.upper()}")
    print(f"LLM Provider: GROQ")
    print("=" * 60)
    print("\nInstructions:")
    print("  - Speak clearly into your microphone")
    print("  - You can interrupt the AI while it's speaking")
    print("  - The AI will collect Brigade Eternia requirements:")
    print("    • Budget range (2.5-3 Cr, 3-4 Cr, etc.)")
    print("    • Preferred BHK (3 BHK or 4 BHK)")
    print("    • Size preference (sqft range)")
    print("    • Move-in timeline (by 2030)")
    print("    • Key priorities (amenities, location, etc.)")
    print("    • Financing needs (yes/no/maybe)")
    print("  - Press Ctrl+C to stop")
    print("=" * 60)
    print("\nStarting local voice client...\n")
    
    client = LocalVoiceClient()
    await client.start_session()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n\\n[SHUTDOWN] Stopped by user.")
    except Exception as e:
        print(f"\\n\\nERROR - FATAL: {e}\\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
