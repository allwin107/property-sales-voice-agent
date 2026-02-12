import requests
import json
import sys

def trigger_call(phone_number):
    url = "http://localhost:8001/submit-enquiry"
    payload = {
        "name": "Test User",
        "phone": phone_number,
        "email": "test@example.com",
        "message": "I want to test the voice agent."
    }
    
    print(f"Submitting enquiry to {url}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python trigger_call.py <phone_number>")
        sys.exit(1)
    
    trigger_call(sys.argv[1])
