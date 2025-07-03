from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.controllers.ghl import ghl_controller
import logging
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

@router.post("/webhook/aircall")
async def receive_aircall_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    try:
        original_json = await request.json()

        # --- Extracción Segura de Datos para evitar KeyError ---
        data = original_json.get("data", {})
        user_info = data.get("user", {})

        call_id = data.get("id")
        timestamp = original_json.get("timestamp")
        direction = data.get("direction")
        direct_link = data.get("direct_link", "").rstrip(";")
        id_user = user_info.get("id")
        phone_number = data.get("raw_digits")
        status = data.get("status")

        # --- Guardado en Base de Datos ---
        if call_id:
            call = CallModel(
                uuid=uuid4(),
                call_id=str(call_id),
                time_stamp=str(timestamp),
                direction=direction,
                direct_link=direct_link,
                id_user=str(id_user) if id_user else None,
                phone_number=phone_number,
                status=status,
                created_at=datetime.utcnow(),
            )
            session.add(call)
            session.commit()
            session.refresh(call)
            logger.info(f"Nueva llamada guardada - Call ID: {call.call_id}, Status: {call.status}")
        
        # --- Lógica de GoHighLevel ---
        if not phone_number:
            logger.warning("El webhook no contenía un número de teléfono. No se puede actualizar GHL.")
        else:
            contact = await ghl_controller.get_contact_by_phone(phone_number)

            if contact and contact.get("id"):
                contact_id = contact["id"]
                await ghl_controller.update_contact_call_count(contact_id)
            else:
                logger.info(f"No se procedió a la actualización en GHL porque no se encontró el contacto con teléfono {phone_number}.")

    except Exception as e:
        # Captura cualquier otro error inesperado para evitar que el servidor se caiga
        logger.error(f"EXCEPCIÓN GENERAL en el webhook de Aircall: {e}", exc_info=True)

    return {"message": "Webhook procesado."}
    
@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data:CallModelCreate, session: Session = Depends(get_session)):
    calls = await call_controller.create_call(data=data, session=session)
    return calls