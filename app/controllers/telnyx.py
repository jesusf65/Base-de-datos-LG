
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
TELNYX_CONNECTION_ID = os.getenv("TELNYX_CONNECTION_ID")

async def hacer_llamada(to_number: str):
    url = "https://api.telnyx.com/v2/calls"
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "connection_id": TELNYX_CONNECTION_ID,
        "to": to_number,
        "from": os.getenv("TELNYX_FROM_NUMBER"),
        "audio_url": "https://yourdomain.com/audio.mp3"  # o manejar con webhook
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload)
        return r.json()
