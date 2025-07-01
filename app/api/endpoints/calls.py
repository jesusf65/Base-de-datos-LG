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

AIRCALL_API_TOKEN = "ca27cfdfb8ec3ad032150c54c8525065"
AIRCALL_BASE_URL = "https://api.aircall.io/v1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@router.post("/webhook/aircall", status_code=200)
async def receive_aircall_webhook(request: Request):
    try:
        data = await request.json()
        logger.info("📥 Webhook recibido")

        if data.get("event") != "call.ended":
            logger.info("⚠️ Evento ignorado: %s", data.get("event"))
            return {"message": "Evento ignorado"}

        call_data = data["data"]
        call_id = call_data["id"]
        logger.info(f"🆔 call_id: {call_id}")

        logger.info("⏳ Esperando 30 segundos para permitir que el recording se genere...")
        await asyncio.sleep(30)

        # 🔁 Consultar el recording desde la API de Aircall
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AIRCALL_BASE_URL}/calls/{call_id}",
                headers={"Authorization": AIRCALL_API_TOKEN}
            )

        if response.status_code == 200:
            call_details = response.json().get("call", {})
            recording_url = call_details.get("recording")

            if recording_url:
                logger.info(f"🎧 Recording disponible: {recording_url}")
            else:
                logger.warning("🚫 No hay recording disponible todavía.")
        else:
            logger.error(f"❌ Error al consultar la llamada: {response.status_code} {response.text}")

        return {"message": "Llamada procesada, ver consola"}

    except Exception as e:
        logger.error(f"❌ Error procesando el webhook: {e}")
        return {"error": "Error al procesar el webhook"}
    
@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data:CallModelCreate, session: Session = Depends(get_session)):
    calls = await call_controller.create_call(data=data, session=session)
    return calls