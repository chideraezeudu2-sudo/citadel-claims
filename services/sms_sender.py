import os
import httpx
from dotenv import load_dotenv

load_dotenv()

PLIVO_AUTH_ID = os.getenv("PLIVO_AUTH_ID")
PLIVO_AUTH_TOKEN = os.getenv("PLIVO_AUTH_TOKEN")


async def send_sms(to: str, from_number: str, message: str):
    """Send SMS via Plivo"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.plivo.com/v1/Account/{PLIVO_AUTH_ID}/Message/",
            auth=(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN),
            json={
                "src": from_number,
                "dst": to,
                "text": message
            }
        )
        return response.json()