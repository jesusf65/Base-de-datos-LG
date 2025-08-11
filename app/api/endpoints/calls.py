from fastapi import APIRouter, Request, HTTPException
import json
from app.services.webhook_service import WebhookService
from app.services.webhook_service import WebhookServiceDriverUs,webhooks_services

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


logger = setup_logger("webhook_logger_drive_us")
webhooks_services = WebhookServiceDriverUs(logger)


@router.post("/webhook_drive_us")
async def receive_webhook(request: Request):    
    try:
        # 1. Obtener el cuerpo de la solicitud
        body = await request.body()
        
        # 2. Registrar los datos crudos recibidos
        logger.info(f"Datos crudos recibidos: {body.decode('utf-8')}")
        
        # 3. Procesar el JSON
        payload = json.loads(body)
        logger.info(f"Datos JSON parseados: {json.dumps(payload, indent=2)}")
        
        # Extraer los datos reales del objeto 'data'
        data = payload.get('Raw data', {})
        
        # Verificar si hay datos
        if not data:
            raise HTTPException(status_code=400, detail="No data found in payload")
        
        # Procesamiento con la instancia webhook_service
        timing_data = webhooks_services.process_timing_datas(data)
        
        response = webhooks_services.create_responses(
            timing_data,
            data.get('Numero de veces contactado', 0)
        )
        
        lc_payload = webhooks_services.prepare_leadconnector_payloads(data, timing_data)
        lc_response = await webhooks_services.send_to_leadconnectors(lc_payload)

        if lc_response:
            response["lc_status"] = "success"
            response["lc_response"] = lc_response
        else:
            response["lc_status"] = "failed"
        
        return response

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON received. Raw data: {body.decode('utf-8', errors='replace')}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"An error occurred: {e}\nRaw data: {body.decode('utf-8', errors='replace')}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))