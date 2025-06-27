from fastapi import APIRouter, Request, status, Depends
import logging
from sqlalchemy.orm import Session

from app.schemas.call_model import CallModelCreate  
from app.controllers.call import call_controller
from app.core.database import get_session

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
    
@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data:CallModelCreate, session: Session):
    call = await call_controller.create_call(data=data, session=session)
    return call