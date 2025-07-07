from fastapi import APIRouter, Request, Depends, status, HTTPException
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
async def webhook_call(request: Request, db: Session = Depends(get_session)):
    """
    Webhook que recibe llamadas y las procesa
    """
    try:
        # Paso 1: Leer y validar los datos recibidos
        try:
            body = await request.body()
            logger.info(f"Datos recibidos: {body}")
            
            # Intentar parsear como JSON
            if body:
                call_data = json.loads(body.decode('utf-8'))
            else:
                raise ValueError("Body vacío")
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            logger.error(f"Datos recibidos: {body}")
            raise HTTPException(
                status_code=400,
                detail=f"Datos no válidos: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error leyendo datos: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Error leyendo datos: {str(e)}"
            )
        
        # Paso 2: Extraer datos de Aircall y mapear a nuestros campos
        try:
            # Extraer datos del webhook de Aircall
            data = call_data.get("data", {})
            user = data.get("user", {})
            number = data.get("number", {})
            
            # Mapear campos de Aircall a nuestros campos
            mapped_data = {
                "call_id": str(data.get("id", "")),
                "time_stamp": str(call_data.get("timestamp", "")),
                "direction": str(data.get("direction", "")),
                "direct_link": str(data.get("direct_link", "")),
                "id_user": str(user.get("id", "")),
                "phone_number": str(data.get("raw_digits", "")),
                "status": str(data.get("status", ""))
            }
            
            logger.info(f"Datos mapeados: {mapped_data}")
            
        except Exception as e:
            logger.error(f"Error mapeando datos de Aircall: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Error procesando datos de Aircall: {str(e)}"
            )
        
        # Paso 3: Validar campos requeridos después del mapeo
        required_fields = ["call_id", "time_stamp", "direction", "direct_link", "id_user", "phone_number", "status"]
        missing_fields = [field for field in required_fields if not mapped_data.get(field)]
        
        if missing_fields:
            logger.error(f"Campos faltantes después del mapeo: {missing_fields}")
            logger.error(f"Datos originales: {call_data}")
            raise HTTPException(
                status_code=400,
                detail=f"Campos requeridos faltantes: {missing_fields}"
            )
        
        # Paso 4: Crear y guardar la llamada
        new_call = CallModel(
            call_id=mapped_data["call_id"],
            time_stamp=mapped_data["time_stamp"],
            direction=mapped_data["direction"],
            direct_link=mapped_data["direct_link"],
            id_user=mapped_data["id_user"],
            phone_number=mapped_data["phone_number"],
            status=mapped_data["status"]
        )
        
        db.add(new_call)
        db.flush()  # Para obtener el UUID sin hacer commit
        
        # Paso 5: Buscar contacto por número de teléfono
        phone_number = mapped_data["phone_number"]
        existing_contact = db.query(Contact).filter(
            Contact.phone_number == phone_number,
            Contact.deleted_at.is_(None)
        ).first()
        
        if existing_contact:
            # Paso 6a: Si existe el contacto, incrementar contador
            contact_to_update = existing_contact
            logger.info(f"Contacto encontrado: {contact_to_update.uuid}")
            
            # Incrementar contador en custom_fields
            try:
                current_data = json.loads(contact_to_update.custom_fields) if contact_to_update.custom_fields else {}
            except (json.JSONDecodeError, TypeError):
                current_data = {}
            
            current_data["call_count"] = current_data.get("call_count", 0) + 1
            contact_to_update.custom_fields = json.dumps(current_data)
            
        else:
            # Paso 6b: Si no existe, crear nuevo contacto
            logger.info(f"Creando nuevo contacto para teléfono: {phone_number}")
            contact_to_update = Contact(
                contact_id=f"AUTO_{new_call.uuid}",
                contact_name=f"Contact_{phone_number}",
                create_date=datetime.now().isoformat(),
                asign_to="",
                phone_number=phone_number,
                source="aircall_webhook",
                tags="",
                custom_fields=json.dumps({"call_count": 1})
            )
            
            db.add(contact_to_update)
            db.flush()
        
        # Paso 7: Asociar el contacto a la llamada
        new_call.contact_uuid = contact_to_update.uuid
        
        # Paso 8: Guardar todo
        db.commit()
        
        logger.info(f"Llamada procesada exitosamente: {new_call.uuid}")
        
        return {
            "status": "success",
            "message": "Llamada procesada correctamente",
            "call_uuid": str(new_call.uuid),
            "contact_uuid": str(contact_to_update.uuid),
            "call_count": json.loads(contact_to_update.custom_fields).get("call_count", 0)
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando llamada: {str(e)}"
        )

# ============================
# ENDPOINT ADICIONAL PARA TESTING
# ============================
@router.post("/webhook/call/test")
async def test_webhook(call_data: dict, db: Session = Depends(get_session)):
    """
    Endpoint de prueba que usa el modelo Pydantic
    """
    try:
        logger.info(f"Datos de prueba: {call_data}")
        
        # Procesar usando la misma lógica
        new_call = CallModel(
            call_id=str(call_data.get("call_id", "test_call")),
            time_stamp=str(call_data.get("time_stamp", datetime.now().isoformat())),
            direction=str(call_data.get("direction", "inbound")),
            direct_link=str(call_data.get("direct_link", "https://test.com")),
            id_user=str(call_data.get("id_user", "test_user")),
            phone_number=str(call_data.get("phone_number", "+1234567890")),
            status=str(call_data.get("status", "completed"))
        )
        
        db.add(new_call)
        db.flush()
        
        # Buscar o crear contacto
        phone_number = str(call_data.get("phone_number", "+1234567890"))
        existing_contact = db.query(Contact).filter(
            Contact.phone_number == phone_number,
            Contact.deleted_at.is_(None)
        ).first()
        
        if existing_contact:
            contact_to_update = existing_contact
            try:
                current_data = json.loads(contact_to_update.custom_fields) if contact_to_update.custom_fields else {}
            except (json.JSONDecodeError, TypeError):
                current_data = {}
            
            current_data["call_count"] = current_data.get("call_count", 0) + 1
            contact_to_update.custom_fields = json.dumps(current_data)
        else:
            contact_to_update = Contact(
                contact_id=f"AUTO_{new_call.uuid}",
                contact_name=f"Contact_{phone_number}",
                create_date=datetime.now().isoformat(),
                asign_to="",
                phone_number=phone_number,
                source="webhook_call",
                tags="",
                custom_fields=json.dumps({"call_count": 1})
            )
            db.add(contact_to_update)
            db.flush()
        
        new_call.contact_uuid = contact_to_update.uuid
        db.commit()
        
        return {
            "status": "success",
            "message": "Test completado",
            "call_uuid": str(new_call.uuid),
            "contact_uuid": str(contact_to_update.uuid),
            "call_count": json.loads(contact_to_update.custom_fields).get("call_count", 0)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error en test: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en test: {str(e)}"
        )
    
@router.get("/webhook/call/health")
async def health_check():
    """
    Endpoint simple para verificar que el webhook está funcionando
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Webhook funcionando correctamente"
    }

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