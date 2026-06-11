import os
import json
from groq import Groq
from google import genai
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

INTENT_PROMPT = """
You are the intent classifier for Citadel Claims, an insurance estimating service.
Classify the user message into exactly one of these intents:
- SUBMIT_CLAIM: user wants to submit a new claim or is sending photos/voice notes
- CHECK_STATUS: user wants to know the status of a claim
- GET_PORTAL: user wants their file portal link
- CANCEL: user wants to cancel their subscription
- BILLING: user wants billing or usage information
- HELP: user wants to know what they can do
- UNKNOWN: cannot determine intent

Respond with ONLY a JSON object like this:
{"intent": "SUBMIT_CLAIM", "confidence": 0.95}

User message: {message}
"""


async def classify_intent(message: str) -> dict:
    prompt = INTENT_PROMPT.format(message=message)
    
    # Try Groq first
    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )
        result = response.choices[0].message.content.strip()
        return json.loads(result)
    except Exception as groq_error:
        print(f"Groq failed: {groq_error}. Falling back to Gemini.")
    
    # Fallback to Gemini
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        result = response.text.strip()
        return json.loads(result)
    except Exception as gemini_error:
        print(f"Gemini also failed: {gemini_error}")
        return {"intent": "UNKNOWN", "confidence": 0.0}