from fastapi import APIRouter, Request
import logging

router = APIRouter()
# Configurar logger básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/webhook/aircall")
async def simple_aircall_logger(request: Request):
    try:
        body = await request.json()
        logger.info("📥 Webhook recibido:")
        logger.info(body)
        return {"status": "OK", "message": "Datos recibidos"}
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {str(e)}")
        return {"status": "ERROR", "detail": str(e)}