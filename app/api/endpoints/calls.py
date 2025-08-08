from fastapi import APIRouter, Request
import json
import logging
from datetime import datetime
from typing import Optional

# Configura el logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("webhook_logger")

router = APIRouter()

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Intenta parsear una fecha usando múltiples formatos"""
    if not date_str or str(date_str).strip() == '':
        return None
        
    date_formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',  # Formato ISO (date_created)
        '%m/%d/%Y %H:%M',         # Formato Fecha/Hora primer llamada
        '%Y-%m-%d',               # Formato simple de fecha
        '%m/%d/%Y',               # Formato americano simple
        '%Y-%m-%d %H:%M:%S',      # Formato alternativo
        '%m/%d/%Y %H:%M:%S'       # Formato alternativo 2
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    logger.warning(f"No se pudo parsear la fecha: {date_str}")
    return None

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        # Read the request body
        body = await request.body()
        data = json.loads(body)

        # Log básico de los datos recibidos
        logger.info(f"Webhook recibido para contacto: {data.get('full_name', 'Nombre no disponible')}")
        logger.info(f"Número de veces contactado: {data.get('Número de veces contactado', 0)}")

        # Procesamiento de fechas
        timing_data = {
            "contact_creation": None,
            "first_call": None,
            "time_between": None,
            "call_count": data.get('Número de veces contactado', 0),
            "last_contact": data.get('Última vez contactado')
        }

        # Obtener posibles campos de fecha de creación
        creation_str = (data.get('date_created') or 
                      data.get('Fecha de creación') or 
                      data.get('create date'))
        
        creation_date = parse_date(creation_str)
        
        # Obtener fecha de primera llamada
        first_call_str = data.get('Fecha/Hora primer llamada')
        first_call_date = parse_date(first_call_str)
        
        # Calcular diferencia si tenemos ambas fechas
        if creation_date and first_call_date:
            diferencia = first_call_date - creation_date
            timing_data.update({
                "time_between_hours": round(diferencia.total_seconds() / 3600, 2),
                "time_between_days": round(diferencia.total_seconds() / 86400, 2)
            })
            
            logger.info(f"Detalles de tiempo: "
                      f"Creación: {creation_date} | "
                      f"Primera llamada: {first_call_date} | "
                      f"Diferencia: {diferencia}")
        
        # Actualizar datos para la respuesta
        timing_data.update({
            "contact_creation": creation_date.isoformat() if creation_date else None,
            "first_call": first_call_date.isoformat() if first_call_date else None
        })

        # Registrar advertencias si faltan datos importantes
        if not creation_date:
            logger.warning("No se encontró fecha de creación válida en los datos")
        if not first_call_date:
            logger.warning("No se encontró fecha de primera llamada válida en los datos")

        return {
            "status": "success",
            "message": "Webhook processed successfully",
            "contact_id": data.get('contact_id'),
            "contact_name": data.get('full_name'),
            "timing_data": timing_data,
            "metadata": {
                "source": data.get('contact_source'),
                "tags": data.get('tags'),
                "location": data.get('location', {}).get('fullAddress')
            }
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON received", exc_info=True)
        return {"status": "error", "message": "Invalid JSON format"}, 400
    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500