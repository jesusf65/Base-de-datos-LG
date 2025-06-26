from fastapi import APIRouter, Request
import logging

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def aircall_webhook(request: Request):
    try:
        payload = await request.json()
        logger.info("📨 Webhook recibido:")
        logger.info(payload)
        return {"status": "ok", "message": "Payload recibido"}
    except Exception as e:
        logger.error(f"❌ Error al procesar webhook: {e}")
        return {"status": "error", "detail": str(e)}