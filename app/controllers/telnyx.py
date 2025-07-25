import httpx
import os
from dotenv import load_dotenv
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

load_dotenv()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
TELNYX_CONNECTION_ID = os.getenv("TELNYX_CONNECTION_ID")
TELNYX_FROM_NUMBER = os.getenv("TELNYX_FROM_NUMBER")

async def hacer_llamada(to_number: str):
    url = "https://api.telnyx.com/v2/calls"
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",  # ✅ Correcto
        "Content-Type": "application/json"
    }

    payload = {
        "connection_id": TELNYX_CONNECTION_ID,
        "to": to_number,
        "from": TELNYX_FROM_NUMBER,
        "audio_url": "https://yourdomain.com/audio.mp3"  # Opcional
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()  # Lanza error si es 4xx/5xx
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Error de Telnyx: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error al iniciar llamada: {e.response.text}"
        )