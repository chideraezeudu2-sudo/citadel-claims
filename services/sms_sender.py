import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")


async def send_sms(to: str, from_number: str, message: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.telnyx.com/v2/messages",
            headers={
                "Authorization": f"Bearer {TELNYX_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": from_number,
                "to": to,
                "text": message
            }
        )
        return response.json()