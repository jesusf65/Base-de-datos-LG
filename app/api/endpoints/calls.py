from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import logging
import asyncio
from datetime import datetime 
from uuid import uuid4

from app.schemas.call_model import CallModelCreate
from app.models.CallModel import CallModel
from app.core.database import get_session
from app.controllers.call import call_controller
from app.core.database import get_session

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/webhook/aircall", status_code=200)
async def receive_aircall_webhook(request: Request):
    data = await request.json()

    if data.get("event") != "call.ended":
        return {"message": "Evento ignorado"}

    logger.info("📥 Evento 'call.ended' recibido, esperando 10s...")
    await asyncio.sleep(10)
    logger.info(f"📄 Log de la llamada:\n{data}")

    return {"message": "Llamada registrada en consola"}

@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data:CallModelCreate, session: Session = Depends(get_session)):
    calls = await call_controller.create_call(data=data, session=session)
    return calls