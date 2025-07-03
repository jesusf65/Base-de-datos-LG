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
    """
    Paso 3: Recibe el webhook de Aircall, guarda la llamada y actualiza el contacto en GHL.
    """
    original_json = await request.json()

    # Extraemos el número de teléfono del payload del webhook
    phone_number = original_json.get("data", {}).get("raw_digits")

    # --- Lógica para guardar la llamada en tu base de datos (tu código original) ---
    call_id = str(original_json["data"]["id"])
    call = CallModel(
        uuid=uuid4(),
        call_id=call_id,
        time_stamp=str(original_json["timestamp"]),
        direction=original_json["data"]["direction"],
        direct_link=original_json["data"]["direct_link"].rstrip(";"),
        id_user=str(original_json["data"]["user"]["id"]),
        phone_number=phone_number,
        status=original_json["data"]["status"],
        created_at=datetime.utcnow(),
    )
    session.add(call)
    await session.commit()
    await session.refresh(call)

    logger.info(f"Nueva llamada guardada - Call ID: {call.call_id}, Status: {call.status}, phone_number: {call.phone_number}")
    
    # --- Nueva lógica para actualizar GoHighLevel ---
    if not phone_number:
        logger.warning("El webhook no contenía un número de teléfono ('raw_digits'). No se puede actualizar GHL.")
        return {"message": "Llamada guardada, pero no se encontró número para actualizar GHL.", "uuid": str(call.uuid)}

    # 1. Buscar el contacto en GHL
    contact = await ghl_controller.get_contact_by_phone(phone_number)

    if contact and contact.get("id"):
        # 2. Si se encuentra, actualizar el contador de llamadas
        contact_id = contact["id"]
        await ghl_controller.update_contact_call_count(contact_id)
    else:
        logger.info(f"No se procedió a la actualización en GHL porque no se encontró el contacto con teléfono {phone_number}.")

    return {"message": "Llamada guardada y proceso de actualización en GHL iniciado.", "uuid": str(call.uuid)}
    
@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data:CallModelCreate, session: Session = Depends(get_session)):
    calls = await call_controller.create_call(data=data, session=session)
    return calls