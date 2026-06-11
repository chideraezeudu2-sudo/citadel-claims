import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")


async def send_sms(to: str, from_number: str, message: str):
    """Send SMS via Twilio"""
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            auth=auth,
            data={
                "To": to,
                "From": from_number,
                "Body": message
            }
        )
        return response.json()