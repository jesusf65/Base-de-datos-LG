from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import logging
from datetime import datetime 
from uuid import uuid4

from app.schemas.call_model import CallModelCreate
from app.models.CallModel import CallModel
from app.core.database import get_session
from app.controllers.call import call_controller

router = APIRouter()

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aircall_webhook")

@router.post("/webhook/aircall", status_code=201)
async def receive_aircall_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    original_json = await request.json()

    logger.info("📥 Webhook recibido:")
    logger.info(original_json)

    try:
        call_id = str(original_json["data"]["id"])
        user_id = str(original_json["data"].get("user", {}).get("id", "SIN_USUARIO"))
        logger.info(f"🆔 call_id: {call_id}")
        logger.info(f"👤 user_id: {user_id}")

        call = CallModel(
            uuid=uuid4(),
            call_id=call_id,
            time_stamp=str(original_json["timestamp"]),
            direction=original_json["data"]["direction"],
            direct_link=original_json["data"]["direct_link"].rstrip(";"),
            id_user=user_id,
            phone_number=original_json["data"]["raw_digits"],
            status=original_json["data"]["status"],
            created_at=datetime.utcnow(),
        )

        session.add(call)
        await session.commit()
        await session.refresh(call)

        logger.info(f"✅ Call registrada con UUID: {call.uuid}")

        return {"message": "Call saved", "uuid": str(call.uuid)}

    except Exception as e:
        logger.exception("❌ Error al procesar webhook de Aircall")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data:CallModelCreate, session: Session = Depends(get_session)):
    calls = await call_controller.create_call(data=data, session=session)
    return calls