import os
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

ESTIMATE_PROMPT = """
You are a professional insurance claims estimator working for Citadel Claims.

You have received:
- Voice note transcript: {transcript}
- Number of photos analyzed: {photo_count}
- Photo descriptions: {photo_descriptions}
- Claim type: {claim_type}

Generate a complete, carrier-ready insurance estimate with the following sections:

1. CLAIM SUMMARY
   - Claim type
   - Property/item affected
   - Cause of loss
   - Date of loss (if mentioned)

2. SCOPE OF DAMAGE
   - Detailed description of all damage observed
   - Room by room or area by area breakdown

3. LINE ITEMS
   - Each line item with: Description | Unit | Quantity | Unit Price | Total
   - Use standard Xactimate-style line item descriptions where possible

4. ESTIMATE TOTALS
   - Subtotal
   - Overhead & Profit (10% O&P if applicable)
   - Total Replacement Cost Value (RCV)
   - Depreciation estimate
   - Actual Cash Value (ACV)

5. ADJUSTER NOTES
   - Any flagged items that may need supplement
   - Any areas that need additional photo documentation
   - Carrier submission recommendations

6. CONFIDENCE RATING
   - Rate your confidence in this estimate from 1-10
   - Note any sections where photo quality or transcript clarity limited accuracy

Be specific. Use real dollar amounts based on current market rates. This estimate will be reviewed by a licensed adjuster before submission.
"""


async def transcribe_audio(audio_url: str) -> str:
    """Download audio and transcribe using Gemini"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(audio_url)
            audio_data = response.content
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            "Transcribe this voice note from an insurance adjuster accurately. Include all details mentioned.",
            {"mime_type": "audio/ogg", "data": audio_data}
        ])
        return response.text
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""


async def analyze_photos(photo_urls: list) -> list:
    """Analyze each photo and return descriptions"""
    descriptions = []
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    for url in photo_urls:
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(url)
                image_data = response.content
            
            response = model.generate_content([
                "You are an insurance damage assessor. Describe this photo in detail: what is damaged, the severity, the extent of damage, and what repair or replacement work would be needed. Be specific.",
                {"mime_type": "image/jpeg", "data": image_data}
            ])
            descriptions.append(response.text)
        except Exception as e:
            print(f"Photo analysis error for {url}: {e}")
            descriptions.append("Photo could not be analyzed.")
    
    return descriptions


async def draft_estimate(
    transcript: str,
    photo_descriptions: list,
    claim_type: str
) -> str:
    """Draft full estimate using Gemini"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = ESTIMATE_PROMPT.format(
        transcript=transcript or "No voice note provided.",
        photo_count=len(photo_descriptions),
        photo_descriptions="\n".join([f"Photo {i+1}: {desc}" for i, desc in enumerate(photo_descriptions)]),
        claim_type=claim_type or "General property claim"
    )
    
    response = model.generate_content(prompt)
    return response.text


async def process_claim(claim_id: str, voice_url: str, photo_urls: list, claim_type: str) -> tuple:
    """Full pipeline: transcribe + analyze + draft"""
    transcript = ""
    if voice_url:
        transcript = await transcribe_audio(voice_url)
    
    photo_descriptions = []
    if photo_urls:
        photo_descriptions = await analyze_photos(photo_urls)
    
    estimate = await draft_estimate(transcript, photo_descriptions, claim_type)
    return estimate, transcript