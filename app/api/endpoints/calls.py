from fastapi import APIRouter, Request
import json
import logging
from datetime import datetime

# Configura el logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("webhook_logger")

router = APIRouter()

def parse_date(date_str, formats):
    """Intenta parsear una fecha usando múltiples formatos"""
    if not date_str:  # Si la cadena está vacía
        return None
        
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        # Read the request body
        body = await request.body()
        data = json.loads(body)

        # Log the received data
        logger.info(f"Received webhook data: {data}")

        # Extraer y registrar las fechas importantes
        timing_data = {
            "contact_creation": None,
            "first_call": None,
            "time_between": None,
            "contact_id": data.get('contact_id')
            
        }

        # Formatos de fecha a probar
        date_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',  # Formato ISO (date_created)
            '%m/%d/%Y %H:%M',         # Formato Fecha/Hora primer llamada
            '%Y-%m-%d',               # Formato simple de fecha
            '%m/%d/%Y'                # Formato americano simple
        ]

        try:
            # Procesar fecha de creación del contacto
            creation_str = data.get('date_created') or data.get('Fecha de creación') or data.get('create date')
            create_date = parse_date(creation_str, date_formats)
            
            # Procesar fecha de primera llamada
            first_call_str = data.get('Fecha/Hora primer llamada')
            first_call_date = parse_date(first_call_str, date_formats)
            
            # Calcular diferencia si tenemos ambas fechas
            if create_date and first_call_date:
                diferencia = first_call_date - create_date
                
                logger.info(f"Fecha creación contacto: {create_date}")
                logger.info(f"Fecha/Hora primera llamada: {first_call_date}")
                logger.info(f"Tiempo entre creación y primera llamada: {diferencia}")
                contact_id = data.get('contact_id')
                logger.info(f"contact_id: {contact_id}")
            else:
                if not create_date:
                    logger.warning("No se pudo obtener fecha de creación válida")
                if not first_call_date:
                    logger.warning("No se pudo obtener fecha de primera llamada válida")
                
        except Exception as date_error:
            logger.error(f"Error procesando fechas: {date_error}", exc_info=True)

        # Actualizar datos de timing para la respuesta
        timing_data.update({
            "contact_creation": create_date.isoformat() if create_date else None,
            "first_call": first_call_date.isoformat() if first_call_date else None
        })

        return {
            "status": "success",
            "message": "Webhook received successfully",
            "timing_data": timing_data,
            "call_count": data.get('Número de veces contactado', 0)
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        return {"status": "error", "message": "Invalid JSON format"}, 400
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500