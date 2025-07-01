from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import logging
import asyncio
from datetime import datetime 
import httpx
from uuid import uuid4

from app.schemas.call_model import CallModelCreate
from app.models.CallModel import CallModel
from app.core.database import get_session
from app.controllers.call import call_controller
from app.core.database import get_session

router = APIRouter()

AIRCALL_API_ID = "28123d667f9bdfe2ddfe8222850ae464"
AIRCALL_API_TOKEN = "ca27cfdfb8ec3ad032150c54c8525065"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_recording_url(call_id: int) -> str | None:
    url = f"https://api.aircall.io/v1/calls/{call_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(AIRCALL_API_ID, AIRCALL_API_TOKEN))
        if response.status_code == 200:
            return response.json()["call"].get("recording", {}).get("url")
        else:
            logger.warning(f"❌ Error al obtener grabación para llamada {call_id}: {response.text}")
            return None



@router.post("/webhook/aircall", status_code=200)
async def receive_aircall_webhook(request: Request):
    data = await request.json()

    if data.get("event") != "call.ended":
        return {"message": "Evento ignorado"}

    call_id = data.get("call", {}).get("id")
    if not call_id:
        raise HTTPException(status_code=400, detail="Call ID no encontrado")

    logger.info(f"📥 Evento 'call.ended' recibido para call_id={call_id}, esperando 2 mins...")
    await asyncio.sleep(120)

    recording_url = await get_recording_url(call_id)

    if recording_url:
        logger.info(f"🔊 Grabación disponible: {recording_url}")
    else:
        logger.warning(f"⚠️ Grabación no disponible aún para call_id={call_id}")

    return {"message": "Evento procesado"}

@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data:CallModelCreate, session: Session = Depends(get_session)):
    calls = await call_controller.create_call(data=data, session=session)
    return calls