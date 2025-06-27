from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.CallModel import CallModel
from app.schemas.call_model import CallModelCreate
from app.core.database import get_session

class CallSaveController:
    async def save_call_from_webhook(self,call_id, first_name, last_name, phone_number):
        async for session in get_session():  # get_session es async generator
            call = CallModel(
                call_id=call_id,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number
            )
            session.add(call)
            await session.commit()

    async def create_call_from_webhook(self,data: CallModelCreate, session:Session ):
        try:
            create = await self.save_call_from_webhook(call_id=data.call_id, first_name=data.first_name, last_name=data.last_name, phone_number=data.phone_number)
            return create
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hay un error:{str(e)}")

call__save_controller = CallSaveController()