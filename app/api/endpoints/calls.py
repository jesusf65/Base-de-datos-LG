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
            data = call_data.get("data", {})
            user = data.get("user", {})

            mapped_data = {
                "call_id": str(data.get("id", "")),
                "time_stamp": str(data.get("duration", 0)),
                "direction": str(data.get("direction", "")),
                "direct_link": str(data.get("direct_link", "")),
                "id_user": str(user.get("name", "")),
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


        # Paso 3: Validar campos requeridos
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
        db.flush()

        # Paso 5: Buscar contacto por número
        phone_number = mapped_data["phone_number"]
        existing_contact = db.query(Contact).filter(
            Contact.phone_number == phone_number,
            Contact.deleted_at.is_(None)
        ).first()

        if existing_contact:
            contact_to_update = existing_contact
            contact_to_update.call_count = (contact_to_update.call_count or 0) + 1
        else:
            contact_to_update = Contact(
                contact_id=f"AUTO_{new_call.uuid}",
                contact_name=f"Contact_{phone_number}",
                create_date=datetime.now().isoformat(),
                asign_to="",
                phone_number=phone_number,
                source="aircall_webhook",
                tags="",
                call_count=1
            )
            db.add(contact_to_update)
            db.flush()

        # Paso 6: Asociar llamada al contacto
        new_call.contact_uuid = contact_to_update.uuid
        db.commit()

        logger.info(f"Llamada procesada exitosamente: {new_call.uuid}")

        return {
            "status": "success",
            "message": "Llamada procesada correctamente",
            "call_uuid": str(new_call.uuid),
            "contact_uuid": str(contact_to_update.uuid),
            "call_count": contact_to_update.call_count
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

@router.post("/webhook/lead")
async def receive_webhook(request: Request):
    try:
        payload = await request.json()
        logger.info("📥 Webhook recibido:")
        logger.info(json.dumps(payload, indent=2, ensure_ascii=False))
        
        call_data = payload.get('data', {})
        
        # Verificar si la llamada fue atendida
        if call_data.get('answered_at'):
            logger.info("✅ Llamada ATENDIDA")
            
            # Verificar posible grabación vacía
            duration = call_data.get('duration', 0)
            answered_at = call_data.get('answered_at', 0)
            ended_at = call_data.get('ended_at', 0)
            
            # Calcular tiempo real de conversación
            talk_time = ended_at - answered_at if all([answered_at, ended_at]) else 0
            
            if talk_time < 5:  # Menos de 5 segundos de conversación
                logger.warning(f"⚠️ Grabación potencialmente vacía o corta. Duración: {talk_time}s")
                
            # Verificar si existe URL de grabación
            if not call_data.get('recording'):
                logger.error("❌ No se encontró URL de grabación")
                
        elif call_data.get('missed_call_reason'):
            logger.warning(f"⛔ Llamada NO atendida: {call_data['missed_call_reason']}")
        else:
            logger.warning("⚠️ Estado de llamada desconocido")
        
        return {"status": "ok", "message": "llamada recibida"}
    except Exception as e:
        logger.error(f"Error al procesar webhook: {str(e)}")
        return {"status": "error", "message": str(e)}
    
@router.get("/webhook/call/health") #Para ver si está vivo
async def health_check():

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