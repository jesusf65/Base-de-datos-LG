from fastapi import APIRouter, Request, HTTPException
import json
import http.client
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("webhook_logger")

LEADCONNECTOR_API_KEY = "Bearer pit-6cd3fee8-5d37-47e4-b2ea-0cc628ceb84f" 
LEADCONNECTOR_HOST = "services.leadconnectorhq.com"
LEADCONNECTOR_VERSION = "2021-04-15"

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        body = await request.body()
        data = json.loads(body)
        logger.info("📥 Payload recibido:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

        contact_id = data.get("contact_id")
        if not contact_id:
            logger.warning("⚠️ No se encontró contact_id en el payload")
            raise HTTPException(status_code=400, detail="El campo contact_id es requerido")

        logger.info("🔍 Contact ID extraído: %s", contact_id)

        
        conn = http.client.HTTPSConnection(LEADCONNECTOR_HOST)
        endpoint = f"/conversations/search?contactId={contact_id}"
        headers = {
            'Accept': 'application/json',
            'Authorization': LEADCONNECTOR_API_KEY,
            'Version': LEADCONNECTOR_VERSION
        }
        
        logger.info("🌐 Enviando GET a: %s%s", LEADCONNECTOR_HOST, endpoint, headers)
        conn.request("GET", endpoint, headers=headers)
        
        response = conn.getresponse()
        response_data = response.read().decode("utf-8")
        
        logger.info("✅ Respuesta de LeadConnector (%s):\n%s", 
                  response.status, 
                  json.dumps(json.loads(response_data), indent=2, ensure_ascii=False))
        
        if response.status >= 400:
            logger.error("❌ Error en LeadConnector API: %s - %s", response.status, response_data)
            raise HTTPException(
                status_code=502,
                detail=f"Error al consultar LeadConnector API: {response.status}"
            )
        
        conversations = json.loads(response_data)

        return {
            "status": "success",
            "contact_id": contact_id,
            "conversations": conversations,
            "message": "Procesamiento completado"
        }

    except json.JSONDecodeError:
        logger.error("❌ JSON inválido recibido")
        raise HTTPException(status_code=400, detail="Formato JSON inválido")
    except Exception as e:
        logger.error("🔥 Error crítico: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")