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
        logger.info(f"Payload recibido en /webhook: {json.dumps(data, indent=2)}")
        
        # Validar campos requeridos
        if not data.get('date_created'):
            raise HTTPException(
                status_code=400,
                detail="Campos obligatorios faltantes: 'date_created'"
            )

        # Procesar los datos (ahora con zona horaria Miami y conversión UNIX)
        timing_data = webhook_service.process_timing_data(data)
        
        if not timing_data.time_between_minutes:
            raise HTTPException(
                status_code=400,
                detail="No se pudo calcular la diferencia de tiempo. Verifique los formatos de fecha."
            )

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
            logger.info("Datos enviados exitosamente a LeadConnector Premium Cars")
            response["lc_response"] = lc_response
        else:
            response["lc_status"] = "failed"
            logger.warning("Falló el envío a LeadConnector Premium Cars")
        
        return response

    except json.JSONDecodeError:
        logger.error("JSON inválido recibido")
        raise HTTPException(status_code=400, detail="Formato JSON inválido")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
@router.post("/webhook_drive_us")
async def receive_webhook(request: Request):    
    try:
        body = await request.body()
        data = json.loads(body)
        logger.info(f"Payload recibido en /webhook: {json.dumps(data, indent=2)}")
        
        # Validar campos requeridos
        if not data.get('date_created'):
            raise HTTPException(
                status_code=400,
                detail="Campos obligatorios faltantes: 'date_created'"
            )

        # Procesar los datos (ahora con zona horaria Miami y conversión UNIX)
        timing_data = webhook_service.process_timing_data(data)
        
        if not timing_data.time_between_minutes:
            raise HTTPException(
                status_code=400,
                detail="No se pudo calcular la diferencia de tiempo. Verifique los formatos de fecha."
            )

        # Crear respuesta
        response = webhook_service.create_response(
            timing_data,
            data.get('Número de veces contactado', 0)
        )
        
        # Enviar a LeadConnector
        lc_payload = webhook_service.prepare_leadconnector_payload(data, timing_data)
        lc_response = await webhook_service.send_to_leadconnector_drive_us(lc_payload)
        
        if lc_response:
            response["lc_status"] = "success"
            logger.info("Datos enviados exitosamente a LeadConnector Drive Us")
            response["lc_response"] = lc_response
        else:
            response["lc_status"] = "failed"
            logger.warning("Falló el envío a LeadConnector Drive Us")
        
        return response

    except json.JSONDecodeError:
        logger.error("JSON inválido recibido")
        raise HTTPException(status_code=400, detail="Formato JSON inválido")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
@router.post("/webhook_dalcava")
async def receive_webhook(request: Request):    
    try:
        body = await request.body()
        data = json.loads(body)
        logger.info(f"Payload recibido en /webhook: {json.dumps(data, indent=2)}")
        
        # Validar campos requeridos
        if not data.get('date_created'):
            raise HTTPException(
                status_code=400,
                detail="Campos obligatorios faltantes: 'date_created'"
            )

        # Procesar los datos (ahora con zona horaria Miami y conversión UNIX)
        timing_data = webhook_service.process_timing_data(data)
        
        if not timing_data.time_between_minutes:
            raise HTTPException(
                status_code=400,
                detail="No se pudo calcular la diferencia de tiempo. Verifique los formatos de fecha."
            )

        # Crear respuesta
        response = webhook_service.create_response(
            timing_data,
            data.get('Número de veces contactado', 0)
        )
        
        # Enviar a LeadConnector
        lc_payload = webhook_service.prepare_leadconnector_payload(data, timing_data)
        lc_response = await webhook_service.send_to_leadconnector_dalcava(lc_payload)
        
        if lc_response:
            response["lc_status"] = "success"
            logger.info("Datos enviados exitosamente a LeadConnector Dalcava")
            response["lc_response"] = lc_response
        else:
            response["lc_status"] = "failed"
            logger.warning("Falló el envío a LeadConnector Dalcava")
        
        return response

    except json.JSONDecodeError:
        logger.error("JSON inválido recibido")
        raise HTTPException(status_code=400, detail="Formato JSON inválido")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")