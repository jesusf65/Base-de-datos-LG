from fastapi import APIRouter, Request, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime 
import logging

from app.schemas.call_model import CallModelCreate
from app.models.CallModel import CallModel
from app.controllers.call import call_controller
from app.core.database import get_session

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/webhooks/aircall", status_code=201)  # Cambié a plural para coincidir con los logs
async def receive_aircall_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    try:
        original_json = await request.json()
        logger.info(f"Received webhook data: {original_json}")
        
        # Validación de datos requeridos
        if not original_json.get("data"):
            raise HTTPException(status_code=422, detail="Missing 'data' field")
            
        data = original_json["data"]
        
        # Validar campos requeridos
        required_fields = ["id", "direction", "direct_link", "user", "raw_digits", "status"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=422, detail=f"Missing required field: {field}")
        
        # Validar que user tenga id
        if "id" not in data.get("user", {}):
            raise HTTPException(status_code=422, detail="Missing user.id field")
        
        call_id = str(data["id"])
        
        call = CallModel(
            uuid=uuid4(),
            call_id=call_id,
            time_stamp=str(original_json.get("timestamp", "")),
            direction=data["direction"],
            direct_link=data["direct_link"].rstrip(";"),
            id_user=str(data["user"]["id"]),
            phone_number=data["raw_digits"],
            status=data["status"],
            created_at=datetime.utcnow(),
        )
        
        session.add(call)
        session.commit()       # Usar await para operaciones async
        session.refresh(call)   # Usar await para operaciones async
        
        logger.info(f"Call saved successfully with UUID: {call.uuid}")
        return {"message": "Call saved", "uuid": str(call.uuid)}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(f"Request data: {original_json if 'original_json' in locals() else 'No data'}")
        session.rollback()
        raise HTTPException(status_code=422, detail=f"Error processing webhook: {str(e)}")

# Endpoint temporal para debugging - eliminar después
@router.post("/webhooks/aircall/debug", status_code=200)
async def debug_aircall_webhook(request: Request):
    try:
        original_json = await request.json()
        logger.info(f"DEBUG - Full webhook data: {original_json}")
        return {"received": original_json}
    except Exception as e:
        logger.error(f"DEBUG - Error: {str(e)}")
        return {"error": str(e)}

@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data: CallModelCreate, session: Session = Depends(get_session)):
    try:
        calls = await call_controller.create_call(data=data, session=session)
        return calls
    except Exception as e:
        logger.error(f"Error creating call: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")