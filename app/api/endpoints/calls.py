from fastapi import APIRouter, Request, HTTPException
import json
from app.services.webhook_service import WebhookService
from app.services.webhook_service import WebhookServiceDriverUs

from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("webhook_logger")
webhook_service = WebhookService(logger)

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        body = await request.body()
        data = json.loads(body)
        
        # Procesar los datos
        timing_data = webhook_service.process_timing_data(data)
        
        # Crear respuesta
        response = webhook_service.create_response(
            timing_data,
            data.get('Número de veces contactado', 0)
        )
        
        # Enviar a LeadConnector
        lc_payload = webhook_service.prepare_leadconnector_payload(data, timing_data)
        lc_response = await webhook_service.send_to_leadconnector(lc_payload)
        
        if lc_response:
            response["lc_status"] = "success"
            response["lc_response"] = lc_response
        else:
            response["lc_status"] = "failed"
        
        return response

    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook_drive_us")
async def receive_webhook(request: Request):    
    try:
        bodys = await request.body()
        datas = json.loads(bodys)
        
        # Procesar los datos
        timing_datas = WebhookServiceDriverUs.process_timing_datas(datas)
        
        # Crear respuesta
        responses = WebhookServiceDriverUs.create_responses(
            timing_datas,
            datas.get('Número de veces contactado', 0)
        )
        
        # Enviar a LeadConnector
        lc_payloads = WebhookServiceDriverUs.prepare_leadconnector_payloads(datas, timing_datas)
        lc_responses = await WebhookServiceDriverUs.send_to_leadconnectors(lc_payloads)
        
        if lc_responses:
            responses["lc_status"] = "success"
            responses["lc_response"] = lc_responses
        else:
            responses["lc_status"] = "failed"
        
        return responses

    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))