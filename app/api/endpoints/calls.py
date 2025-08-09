from fastapi import APIRouter, Request, HTTPException
import json
from app.services.webhook_service import WebhookService
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("webhook_logger")
webhook_service = WebhookService(logger)

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        body = await request.body()
        data = json.loads(body)
        
        # Procesar los datos como antes
        timing_data = webhook_service.process_timing_data(data)
        
        # Preparar payload para LeadConnector
        lc_payload = webhook_service.prepare_leadconnector_payload(data, timing_data)
        
        # Enviar a LeadConnector
        lc_response = await webhook_service.send_to_leadconnector(lc_payload)
        
        # Crear respuesta combinada
        response = webhook_service.create_response(
            timing_data,
            data.get('Número de veces contactado', 0)
        )
        response_dict = response.dict()
        
        if lc_response:
            logger.info(f"Datos enviados a LeadConnector. Respuesta: {lc_response}")
            response_dict["lc_status"] = "success"
            response_dict["lc_response"] = lc_response
        else:
            response_dict["lc_status"] = "failed"
        
        return response_dict

    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))