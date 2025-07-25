from fastapi import APIRouter, Request
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/telnyx", status_code=200)
async def telnyx_webhook(request: Request):
    try:
        payload = await request.json()
        logger.info(f"✅ Webhook Telnyx recibido: {payload}")
        
        # Aquí podrías reaccionar según el tipo de evento:
        event_type = payload.get("data", {}).get("event_type")
        logger.info(f"📌 Tipo de evento: {event_type}")

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {str(e)}")
        return {"error": str(e)}
