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

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        # Read the request body
        body = await request.body()
        data = json.loads(body)

        # Log the received data
        logger.info(f"Received webhook data: {data}")

        # Extraer y registrar las fechas importantes
        if 'Fecha/Hora primer llamada' in data and 'date_created' in data:
            try:
                # Procesar fecha de primera llamada
                primera_llamada_str = data['Fecha/Hora primer llamada']
                primera_llamada = datetime.strptime(primera_llamada_str, '%m/%d/%Y %H:%M')
                
                # Procesar fecha de creación del contacto
                creacion_contacto_str = data['date_created']
                creacion_contacto = datetime.strptime(creacion_contacto_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                
                # Calcular diferencia de tiempo
                diferencia = primera_llamada - creacion_contacto
                
                logger.info(f"Fecha creación contacto: {creacion_contacto}")
                logger.info(f"Fecha/Hora primera llamada: {primera_llamada}")
                logger.info(f"Tiempo entre creación y primera llamada: {diferencia}")
                
            except Exception as date_error:
                logger.error(f"Error procesando fechas: {date_error}")

        return {
            "status": "success",
            "message": "Webhook received successfully",
            "timing_data": {
                "contact_creation": data.get('date_created'),
                "first_call": data.get('Fecha/Hora primer llamada'),
                "time_between": str(diferencia) if 'diferencia' in locals() else None
            }
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        return {"status": "error", "message": "Invalid JSON format"}, 400
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return {"status": "error", "message": str(e)}, 500