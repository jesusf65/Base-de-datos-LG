import httpx
import os
from dotenv import load_dotenv
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

load_dotenv()

TELNYX_API_KEY = "KEY0198431E52A8E18011D46DA3FA847F50_MwvbUsfu3dFgdUMjVkYt69"
TELNYX_CONNECTION_ID = "2742320010645997131"
TELNYX_FROM_NUMBER = "+13053150784" 

async def hacer_llamada(to_number: str):
    url = "https://api.telnyx.com/v2/calls"
    headers = {
        "Telnyx-Api-Key": TELNYX_API_KEY,  # Header corregido
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