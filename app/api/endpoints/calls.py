from fastapi import APIRouter, Request
import json
import logging

# Configura el logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Crea un handler para console
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

# Define el formato del log
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Añade el handler al logger
logger.addHandler(handler)

router = APIRouter()

@router.post("/webhook/lead")
async def receive_webhook(request: Request):
    try:
        payload = await request.json()
        logger.info("📥 Webhook recibido:")
        logger.info(json.dumps(payload, indent=2, ensure_ascii=False))
        
        return {"status": "ok", "message": "log recibido"}
    
    except Exception as e:
        logger.error(f"Error al procesar webhook: {str(e)}")
        return {"status": "error", "message": str(e)}, 500