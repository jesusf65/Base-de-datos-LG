from fastapi import APIRouter, Request
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/telnyx", status_code=200)
async def telnyx_webhook(request: Request):
    try:
        payload = await request.json()
        logger.info(f"📡 Telnyx webhook recibido: {payload}")
        return {"status": "ok", "received": payload}
    except Exception as e:
        logger.error(f"❌ Error procesando webhook Telnyx: {str(e)}")
        return {"error": str(e)}