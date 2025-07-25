from fastapi import APIRouter, Request, HTTPException, Body
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/telnyx", status_code=200)
async def telnyx_webhook(request: Request):
    try:
        # 1. Leer cuerpo en crudo (ignorando Content-Type)
        raw_body = await request.body()
        
        # 2. Decodificar como JSON manualmente
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON inválido: {raw_body.decode()}")
            raise HTTPException(400, detail="Cuerpo no es JSON válido")

        # 3. Procesar el evento
        logger.info(f"✅ Webhook recibido: {payload}")
        event_type = payload.get("data", {}).get("event_type", "desconocido")
        logger.info(f"📌 Tipo de evento: {event_type}")
        
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"🔥 Error: {str(e)}")
        raise HTTPException(500, detail="Error interno")