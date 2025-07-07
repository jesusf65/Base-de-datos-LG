from fastapi import APIRouter, Request, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import json
from datetime import datetime 
import logging

from app.schemas.call_model import CallModelCreate
from app.models.CallModel import CallModel
from app.models.Contacts import Contact
from app.controllers.call import call_controller
from app.core.database import get_session

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/webhook/call")
async def webhook_call(call_data: dict, db: Session = Depends(get_session)):
    """
    Webhook que recibe llamadas y las procesa
    """
    try:
        # Paso 1: Crear y guardar la llamada
        new_call = CallModel(
            call_id=call_data.get("call_id"),
            time_stamp=call_data.get("time_stamp"),
            direction=call_data.get("direction"),
            direct_link=call_data.get("direct_link"),
            id_user=call_data.get("id_user"),
            phone_number=call_data.get("phone_number"),
            status=call_data.get("status")
        )
        
        db.add(new_call)
        db.flush()  # Para obtener el UUID sin hacer commit
        
        # Paso 2: Buscar contacto por número de teléfono
        existing_contact = db.query(Contact).filter(
            Contact.phone_number == call_data.get("phone_number"),
            Contact.deleted_at.is_(None)
        ).first()
        
        if existing_contact:
            # Paso 3a: Si existe el contacto, incrementar contador
            contact_to_update = existing_contact
            
            # Incrementar contador en custom_fields
            try:
                current_data = json.loads(contact_to_update.custom_fields) if contact_to_update.custom_fields else {}
            except (json.JSONDecodeError, TypeError):
                current_data = {}
            
            current_data["call_count"] = current_data.get("call_count", 0) + 1
            contact_to_update.custom_fields = json.dumps(current_data)
            
        else:
            # Paso 3b: Si no existe, crear nuevo contacto
            contact_to_update = Contact(
                contact_id=f"AUTO_{new_call.uuid}",  # ID automático
                contact_name=f"Contact_{call_data.get('phone_number')}",  # Nombre automático
                create_date=datetime.now().isoformat(),
                asign_to="",  # Vacío por defecto
                phone_number=call_data.get("phone_number"),
                source="webhook_call",  # Fuente automática
                tags="",  # Vacío por defecto
                custom_fields=json.dumps({"call_count": 1})  # Primer llamada
            )
            
            db.add(contact_to_update)
            db.flush()  # Para obtener el UUID
        
        # Paso 4: Asociar el contacto a la llamada
        new_call.contact_uuid = contact_to_update.uuid
        
        # Paso 5: Guardar todo
        db.commit()
        
        return {
            "status": "success",
            "message": "Llamada procesada correctamente",
            "call_uuid": str(new_call.uuid),
            "contact_uuid": str(contact_to_update.uuid),
            "call_count": json.loads(contact_to_update.custom_fields).get("call_count", 0)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando llamada: {str(e)}"
        )

@router.post("/webhooks/aircall/debug", status_code=200)
async def debug_aircall_webhook(request: Request):
    try:
        original_json = await request.json()
        logger.info(f"DEBUG - Full webhook data: {original_json}")
        return {"received": original_json}
    except Exception as e:
        logger.error(f"DEBUG - Error: {str(e)}")
        return {"error": str(e)}

@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data: CallModelCreate, session: Session = Depends(get_session)):
    try:
        calls = await call_controller.create_call(data=data, session=session)
        return calls
    except Exception as e:
        logger.error(f"Error creating call: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")