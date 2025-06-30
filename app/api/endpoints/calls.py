from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_session
from app.models.CallModel import CallModel
from app.schemas.call_model import CallModelCreate
from uuid import uuid4
from datetime import datetime 

from sqlalchemy.orm import Session
import logging
from app.schemas.call_model import CallModelCreate  
from app.controllers.call import call_controller
from app.core.database import get_session

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/webhook/aircall", status_code=201)
async def receive_aircall_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    original_json = await request.json()

    call_id = str(original_json["data"]["id"])

    # Verificar si ya existe el call_id
    result = await session.execute(
        select(CallModel).where(CallModel.call_id == call_id)
    )
    existing_call = result.scalar_one_or_none()
    if existing_call:
        raise HTTPException(status_code=400, detail="Call already exists")

    # Crear nuevo registro
    call = CallModel(
        uuid=uuid4(),
        call_id=call_id,
        time_stamp=str(original_json["timestamp"]),
        direction=original_json["data"]["direction"],
        direct_link=original_json["data"]["direct_link"].rstrip(";"),
        id_user=str(original_json["data"]["user"]["id"]),
        phone_number=original_json["data"]["raw_digits"],
        status=original_json["data"]["status"],
        created_at=datetime.utcnow(),
    )

    session.add(call)
    await session.commit()
    await session.refresh(call)

    return {"message": "Call saved", "uuid": str(call.uuid)}
        

@router.post("/call_create", status_code=status.HTTP_201_CREATED)
async def create_call(data:CallModelCreate, session: Session = Depends(get_session)):
    calls = await call_controller.create_call(data=data, session=session)
    return calls